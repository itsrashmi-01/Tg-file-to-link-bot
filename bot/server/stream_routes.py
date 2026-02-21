from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from config import Config
from bot_client import bot
from bot.utils import TgFileStreamer
from bot.clone import db

router = APIRouter()
files_col = db.files # Access the files collection

# Data Model for Password Verification
class PasswordCheck(BaseModel):
    id: int
    password: str

# --- 1. API Endpoint (Get File Info for Blogger) ---
@router.get("/api/file/{message_id}")
async def get_file_info(message_id: int):
    try:
        # Fetch Message from Log Channel
        msg = await bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        
        if not msg or not msg.media:
            return JSONResponse({"error": "File not found"}, status_code=404)
            
        media = msg.document or msg.video or msg.audio
        file_name = getattr(media, "file_name", "file.bin")
        file_size = getattr(media, "file_size", 0)
        
        # Check if file is password protected
        is_locked = False
        if hasattr(media, "file_unique_id"):
            file_data = await files_col.find_one({"file_unique_id": media.file_unique_id})
            if file_data and file_data.get("password"):
                is_locked = True
        
        # Return JSON data for the Blogger script
        return {
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"{Config.BASE_URL}/dl/{message_id}",
            "is_locked": is_locked
        }

    except Exception as e:
        print(f"API Error: {e}")
        return JSONResponse({"error": "Server Error"}, status_code=500)


# --- 2. Password Verification Endpoint (Used by Blogger) ---
@router.post("/api/verify_password")
async def verify_password(data: PasswordCheck):
    try:
        msg = await bot.get_messages(Config.LOG_CHANNEL_ID, data.id)
        if not msg or not msg.media:
            return {"success": False, "error": "File not found"}
        
        media = msg.document or msg.video or msg.audio
        file_data = await files_col.find_one({"file_unique_id": media.file_unique_id})
        
        # Check if password matches
        if file_data and file_data.get("password") == data.password:
            return {
                "success": True, 
                # Return download link WITH password parameter
                "download_url": f"{Config.BASE_URL}/dl/{data.id}?password={data.password}"
            }
        
        return {"success": False, "error": "Incorrect Password"}

    except Exception as e:
        print(f"Verify Error: {e}")
        return {"success": False, "error": "Server Error"}


# --- 3. Download Endpoint (The Actual Stream) ---
@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request, password: str = None):
    try:
        msg = await bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="File not found")
            
        media = msg.document or msg.video or msg.audio
        
        # --- PASSWORD CHECK ---
        if hasattr(media, "file_unique_id"):
            file_data = await files_col.find_one({"file_unique_id": media.file_unique_id})
            if file_data and file_data.get("password"):
                if password != file_data['password']:
                    raise HTTPException(status_code=401, detail="Password Required")
        # ----------------------

        file_name = getattr(media, "file_name", "file.bin")
        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        # Range Handling (For Video Streaming)
        range_header = request.headers.get("range")
        start = 0
        if range_header:
            try:
                start = int(range_header.replace("bytes=", "").split("-")[0])
            except: pass

        streamer = TgFileStreamer(bot, media.file_id, start_offset=start)
        
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size - start)
        }

        return StreamingResponse(
            streamer, 
            status_code=206 if range_header else 200, 
            headers=headers, 
            media_type=mime_type
        )

    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Server Error")
