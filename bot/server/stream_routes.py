import math
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from config import Config
from bot_client import tg_bot
from bot.utils import TgFileStreamer
from bot.clone import db, CLONE_BOTS

router = APIRouter()
files_col = db.files

class PasswordCheck(BaseModel):
    id: int
    password: str

# --- HELPER: Get Client & Channel ---
async def get_target_client_and_channel(message_id):
    """
    Finds the correct bot instance (Main or Clone) and the channel ID 
    where the file is stored.
    """
    file_data = await files_col.find_one({"log_msg_id": message_id})
    
    # Defaults
    client = tg_bot
    channel = Config.LOG_CHANNEL_ID
    
    if file_data:
        # 1. Switch Client if it's a clone
        user_id = file_data.get("user_id")
        if user_id in CLONE_BOTS:
            client = CLONE_BOTS[user_id]
        
        # 2. Switch Channel if stored
        if file_data.get("channel_id"):
            channel = file_data["channel_id"]
            
    return client, channel, file_data

@router.get("/api/file/{message_id}")
async def get_file_info(message_id: int):
    try:
        # Dynamically get the correct client and channel
        client, channel_id, file_data = await get_target_client_and_channel(message_id)
        
        # Fetch Message
        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            return JSONResponse({"error": "File not found"}, status_code=404)
            
        media = msg.document or msg.video or msg.audio or msg.photo
        
        # Default Info
        file_name = getattr(media, "file_name", "file.bin")
        file_size = getattr(media, "file_size", 0)
        is_locked = False

        # Apply Custom Overrides from DB
        if file_data:
            if file_data.get("password"): is_locked = True
            if file_data.get("file_name"): file_name = file_data["file_name"]
        
        return {
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"{Config.BASE_URL}/dl/{message_id}",
            "is_locked": is_locked
        }
    except Exception as e:
        print(f"API Error: {e}")
        return JSONResponse({"error": "Server Error"}, status_code=500)

@router.post("/api/verify_password")
async def verify_password(data: PasswordCheck):
    try:
        # We check DB first for password
        file_data = await files_col.find_one({"log_msg_id": data.id})
        
        if file_data and file_data.get("password") == data.password:
            return {"success": True, "download_url": f"{Config.BASE_URL}/dl/{data.id}?password={data.password}"}
        
        return {"success": False, "error": "Incorrect Password"}
    except Exception as e:
        print(f"Verify Error: {e}")
        return {"success": False, "error": "Server Error"}

@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request, password: str = None):
    try:
        # 1. Get Correct Client & Channel
        client, channel_id, file_data = await get_target_client_and_channel(message_id)

        # 2. Check Password / Expiry
        if file_data:
            if file_data.get("password") and password != file_data['password']:
                raise HTTPException(status_code=401, detail="Password Required")
            
            # Check Expiry
            if file_data.get("expiry"):
                import time
                if time.time() > file_data["expiry"]:
                    raise HTTPException(status_code=410, detail="Link Expired")

        # 3. Fetch from Telegram
        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="File not found or deleted")
            
        media = msg.document or msg.video or msg.audio or msg.photo
        
        # 4. Metadata Overrides
        file_name = getattr(media, "file_name", "file.bin")
        if file_data and file_data.get("file_name"):
            file_name = file_data["file_name"]

        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        # 5. Range Handling
        range_header = request.headers.get("range")
        start = 0
        if range_header:
            try: start = int(range_header.replace("bytes=", "").split("-")[0])
            except: pass

        # 6. Initialize Streamer with Correct Client
        streamer = TgFileStreamer(client, media, start_offset=start)
        
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size - start)
        }

        return StreamingResponse(
            streamer.yield_chunks(), 
            status_code=206 if range_header else 200, 
            headers=headers, 
            media_type=mime_type
        )
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Server Error")
