from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()

# DUAL DB
main_client = AsyncIOMotorClient(Config.MONGO_URL)
main_db = main_client.TelegramBotCluster
clone_client = AsyncIOMotorClient(Config.CLONE_MONGO_URL)
clone_db = clone_client.CloneBotCluster

async def find_file(unique_id):
    f = await main_db.large_files.find_one({"unique_id": unique_id})
    if f: return f
    return await clone_db.large_files.find_one({"unique_id": unique_id})

# 1. API for Blogger
@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    file_data = await find_file(unique_id)
    if not file_data: return JSONResponse({"error": "File not found"}, 404)

    is_locked = bool(file_data.get("password"))
    # Always give download link if not locked
    dl_link = f"{Config.URL}/dl/{unique_id}" if not is_locked else None

    return JSONResponse({
        "file_name": file_data.get('file_name'),
        "file_size": file_data.get('file_size'),
        "is_locked": is_locked,
        "download_url": dl_link
    })

# 2. Password Check
@router.post("/api/verify_password")
async def verify_password(payload: dict = Body(...)):
    file = await find_file(payload.get("id"))
    if not file: return JSONResponse({"error": "Not Found"}, 404)
    
    if payload.get("password") == file.get("password"):
        return JSONResponse({"success": True, "download_url": f"{Config.URL}/dl/{payload.get('id')}"})
    return JSONResponse({"success": False, "error": "❌ Wrong Password"}, 401)

# 3. DOWNLOAD ROUTE
@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request):
    file_data = await find_file(unique_id)
    if not file_data: raise HTTPException(404, "File not found")

    # Select Bot (Main or Clone)
    bot_id = file_data.get("bot_id")
    if bot_id and bot_id in RUNNING_CLONES:
        client = RUNNING_CLONES[bot_id]["client"]
        target = int(RUNNING_CLONES[bot_id]["log_channel"])
    else:
        client = bot
        target = int(Config.LOG_CHANNEL)

    try:
        # Get Media Info
        msg = await client.get_messages(target, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        if not media: raise Exception("Media missing")

        # Initialize Streamer
        streamer = TgFileStreamer(
            client, 
            media.file_id, 
            file_data['file_size'], 
            request.headers.get("range")
        )
        
        # Headers (No Content-Length for stability)
        headers = {
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
            "Accept-Ranges": "bytes"
        }
        
        return StreamingResponse(
            streamer, 
            status_code=206 if request.headers.get("range") else 200, 
            media_type=file_data['mime_type'], 
            headers=headers
        )

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(500, "Download Failed")
