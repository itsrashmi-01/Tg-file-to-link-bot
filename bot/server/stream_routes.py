from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from config import Config
from bot_client import tg_bot
from bot.utils import TgFileStreamer
from bot.clone import db, CLONE_BOTS
import asyncio

router = APIRouter()
files_col = db.files

class PasswordCheck(BaseModel):
    id: int
    password: str
    user_id: int = None

# --- HYBRID RESOLVER: The core fix ---
async def get_client_and_channel(message_id: int, user_id: int = None):
    """
    Finds the correct bot instance and channel ID. 
    Supports both Main Bot and Clone Bots seamlessly.
    """
    # 1. Look up file metadata in Database
    file_data = await files_col.find_one({"log_msg_id": message_id})
    if not file_data:
        # Fallback search if id is unique_id instead of log_msg_id
        file_data = await files_col.find_one({"file_unique_id": str(message_id)})
        if not file_data:
            return None, None, None

    # 2. Determine which bot client to use
    # If a user_id is provided and a clone exists, use it. Otherwise, use Main Bot.
    target_user = user_id or file_data.get("user_id")
    client = CLONE_BOTS.get(target_user, tg_bot)

    # 3. Determine correct channel
    # Use the channel stored with the file, or fallback to main config
    channel_id = file_data.get("log_channel", Config.LOG_CHANNEL_ID)

    # 4. CACHE WARMUP: Resolve Peer identity to prevent "Peer ID Invalid"
    try:
        await client.get_chat(channel_id)
    except Exception:
        pass # If it fails, the next step (get_messages) will try to handle it

    return client, channel_id, file_data

# --- ROUTES ---

@router.get("/api/file/{message_id}")
async def get_file_info(message_id: int, user_id: int = Query(None)):
    try:
        client, channel_id, file_data = await get_client_and_channel(message_id, user_id)
        if not client:
            return JSONResponse({"error": "File metadata not found in database"}, status_code=404)

        # Use the specific client to get message from its specific channel
        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            return JSONResponse({"error": "File not found on Telegram servers"}, status_code=404)
            
        media = msg.document or msg.video or msg.audio
        
        return {
            "file_name": file_data.get("file_name", getattr(media, "file_name", "file")),
            "file_size": getattr(media, "file_size", 0),
            "download_url": f"{Config.BASE_URL}/dl/{message_id}?user_id={user_id or file_data['user_id']}",
            "is_locked": bool(file_data.get("password"))
        }
    except Exception as e:
        print(f"API Info Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/verify_password")
async def verify_password(data: PasswordCheck):
    try:
        _, _, file_data = await get_client_and_channel(data.id, data.user_id)
        if file_data and file_data.get("password") == data.password:
            return {
                "success": True, 
                "download_url": f"{Config.BASE_URL}/dl/{data.id}?user_id={data.user_id or file_data['user_id']}&password={data.password}"
            }
        return {"success": False, "error": "Incorrect Password"}
    except Exception as e:
        return {"success": False, "error": "Verification Failed"}

@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request, user_id: int = Query(None), password: str = None):
    try:
        client, channel_id, file_data = await get_client_and_channel(message_id, user_id)
        if not client:
            raise HTTPException(status_code=404, detail="File not found")

        # Security: Check Password
        if file_data.get("password") and password != file_data['password']:
            raise HTTPException(status_code=401, detail="Password Required")

        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="Message empty")
            
        media = msg.document or msg.video or msg.audio
        file_size = getattr(media, "file_size", 0)
        file_name = file_data.get("file_name", getattr(media, "file_name", "file"))
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        # --- STREAMING LOGIC (With Range Support) ---
        range_header = request.headers.get("range")
        start, end = 0, file_size - 1
        if range_header:
            try:
                range_parts = range_header.replace("bytes=", "").split("-")
                start = int(range_parts[0])
                if range_parts[1]: end = int(range_parts[1])
            except: pass

        streamer = TgFileStreamer(client, media.file_id, start_offset=start)
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{file_size}" if range_header else None
        }

        return StreamingResponse(
            streamer, 
            status_code=206 if range_header else 200, 
            headers={k: v for k, v in headers.items() if v}, 
            media_type=mime_type
        )
    except Exception as e:
        print(f"Streaming Error: {e}")
        raise HTTPException(status_code=500, detail="Streaming Failed")
