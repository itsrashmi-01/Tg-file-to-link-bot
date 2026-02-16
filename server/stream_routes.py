import datetime
from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()

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

@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    file_data = await find_file(unique_id)
    if not file_data: return JSONResponse({"error": "File not found"}, 404)

    is_locked = bool(file_data.get("password"))
    
    return JSONResponse({
        "file_name": file_data.get('file_name'),
        "file_size": file_data.get('file_size'),
        "is_locked": is_locked,
        "download_url": f"{Config.URL}/dl/{unique_id}" if not is_locked else None
    })

@router.post("/api/verify_password")
async def verify_password(payload: dict = Body(...)):
    file = await find_file(payload.get("id"))
    if not file: return JSONResponse({"error": "Not Found"}, 404)
    if payload.get("password") == file.get("password"):
        return JSONResponse({"success": True, "download_url": f"{Config.URL}/dl/{payload.get('id')}"})
    return JSONResponse({"success": False, "error": "Wrong Password"}, 401)

@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request):
    file_data = await find_file(unique_id)
    if not file_data: raise HTTPException(404, "File not found")

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
        
        # Passing String ID (media.file_id) to utils.py
        streamer = TgFileStreamer(
            active_client, 
            media.file_id, 
            file_data['file_size'], 
            request.headers.get("range")
        )
        
        headers = {
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
            "Accept-Ranges": "bytes"
            # Content-Length disabled to prevent crashes on network drop
        }
        
        return StreamingResponse(
            streamer, 
            status_code=206 if request.headers.get("range") else 200, 
            media_type=file_data['mime_type'], 
            headers=headers
        )

    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="File Stream Failed")
