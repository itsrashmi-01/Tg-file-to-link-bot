from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()

# Databases
main_client = AsyncIOMotorClient(Config.MONGO_URL)
main_db = main_client.TelegramBotCluster
clone_client = AsyncIOMotorClient(Config.CLONE_MONGO_URL)
clone_db = clone_client.CloneBotCluster

# Simple File Finder
async def find_file(unique_id):
    f = await main_db.large_files.find_one({"unique_id": unique_id})
    if f: return f
    return await clone_db.large_files.find_one({"unique_id": unique_id})

# 1. API to get File Details (For Blogger)
@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    file_data = await find_file(unique_id)
    if not file_data: return JSONResponse({"error": "File not found"}, 404)

    is_locked = bool(file_data.get("password"))
    
    return JSONResponse({
        "file_name": file_data.get('file_name'),
        "file_size": file_data.get('file_size'),
        "is_locked": is_locked,
        # Direct Download Link
        "download_url": f"{Config.URL}/dl/{unique_id}" if not is_locked else None
    })

# 2. API to Verify Password
@router.post("/api/verify_password")
async def verify_pass(payload: dict = Body(...)):
    file = await find_file(payload.get("id"))
    if not file: return JSONResponse({"error": "Not Found"}, 404)
    
    if payload.get("password") == file.get("password"):
        return JSONResponse({"success": True, "download_url": f"{Config.URL}/dl/{payload.get('id')}"})
    return JSONResponse({"success": False, "error": "Wrong Password"}, 401)

# 3. The DOWNLOAD Route (Simplified)
@router.get("/dl/{unique_id}")
async def stream_file(unique_id: str, request: Request):
    file_data = await find_file(unique_id)
    if not file_data: raise HTTPException(404, "File not found")

    # Get Client
    bot_id = file_data.get("bot_id")
    if bot_id and bot_id in RUNNING_CLONES:
        client = RUNNING_CLONES[bot_id]["client"]
        channel = int(RUNNING_CLONES[bot_id]["log_channel"])
    else:
        client = bot
        channel = int(Config.LOG_CHANNEL)

    try:
        # Fetch Media Object
        msg = await client.get_messages(channel, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        
        # Initialize Streamer with String ID
        streamer = TgFileStreamer(
            client, 
            media.file_id, 
            file_data['file_size'], 
            request.headers.get("range")
        )
        
        # HEADERS (Crucial Changes Here)
        headers = {
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
            "Accept-Ranges": "bytes"
        }
        
        # We REMOVED 'Content-Length' to prevent crashing.
        
        return StreamingResponse(
            streamer, 
            status_code=206 if request.headers.get("range") else 200, 
            media_type=file_data.get('mime_type', 'application/octet-stream'), 
            headers=headers
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(500, "Server Error")
