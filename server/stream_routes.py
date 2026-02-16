import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()

# DUAL DB CONNECTIONS
main_client = AsyncIOMotorClient(Config.MONGO_URL)
main_db = main_client.TelegramBotCluster
clone_client = AsyncIOMotorClient(Config.CLONE_MONGO_URL)
clone_db = clone_client.CloneBotCluster

users_col = main_db.large_file_users

async def find_file(unique_id):
    file_data = await main_db.large_files.find_one({"unique_id": unique_id})
    if file_data: return file_data
    file_data = await clone_db.large_files.find_one({"unique_id": unique_id})
    if file_data: return file_data
    return None

def create_public_link(unique_id):
    return f"{Config.URL}/dl/{unique_id}"

@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    file_data = await find_file(unique_id)
    if not file_data: return JSONResponse({"error": "File not found"}, status_code=404)

    user = await users_col.find_one({"_id": file_data["user_id"]})
    is_premium_user = False
    if user and user.get("plan_type") == "premium":
         if user.get("plan_expiry") and user["plan_expiry"] > datetime.datetime.now():
             is_premium_user = True

    response = {
        "file_name": file_data.get('file_name', 'Unknown'),
        "file_size": file_data.get('file_size', 0),
        "is_locked": bool(file_data.get("password")),
        "show_ads": not is_premium_user
    }

    if not response["is_locked"]:
        response["download_url"] = create_public_link(unique_id)
    
    return JSONResponse(response)

@router.post("/api/verify_password")
async def verify_password(payload: dict = Body(...)):
    unique_id = payload.get("id")
    user_pass = payload.get("password")

    file_data = await find_file(unique_id)
    if not file_data: return JSONResponse({"error": "File not found"}, status_code=404)

    if user_pass == file_data.get("password"):
        return JSONResponse({"success": True, "download_url": create_public_link(unique_id)})
    else:
        return JSONResponse({"success": False, "error": "❌ Wrong Password"}, status_code=401)

@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request):
    file_data = await find_file(unique_id)
    if not file_data: raise HTTPException(status_code=404, detail="File not found")

    owner_bot_id = file_data.get("bot_id")
    if owner_bot_id and owner_bot_id in RUNNING_CLONES:
        active_client = RUNNING_CLONES[owner_bot_id]["client"]
        target_channel = int(RUNNING_CLONES[owner_bot_id]["log_channel"])
    else:
        active_client = bot
        target_channel = int(Config.LOG_CHANNEL)

    try:
        try: await active_client.get_chat(target_channel)
        except: pass

        msg = await active_client.get_messages(target_channel, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        if not media: raise Exception("Media not found")
        
        streamer = TgFileStreamer(
            active_client, 
            media.file_id, 
            file_data['file_size'], 
            request.headers.get("range")
        )
        
        response_size = (streamer.end - streamer.start) + 1
        
        headers = {
            "Accept-Ranges": "bytes",
            # "Content-Length": str(response_size),  <-- COMMENTED OUT TO PREVENT CRASH
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
        }
        
        status_code = 206 if request.headers.get("range") else 200
        if status_code == 206:
            headers["Content-Range"] = f"bytes {streamer.start}-{streamer.end}/{file_data['file_size']}"

        return StreamingResponse(
            streamer, 
            status_code=status_code, 
            media_type=file_data['mime_type'], 
            headers=headers
        )

    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="File Stream Failed")
