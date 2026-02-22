from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from config import Config
from bot_client import tg_bot
from bot.utils import TgFileStreamer
from bot.clone import db

router = APIRouter()

class PasswordCheck(BaseModel):
    id: int
    password: str

@router.get("/api/file/{message_id}")
async def get_file_info(message_id: int):
    try:
        msg = await tg_bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        if not msg or not msg.media:
            return JSONResponse({"error": "File not found"}, status_code=404)
            
        media = msg.document or msg.video or msg.audio
        file_name = getattr(media, "file_name", "file.bin")
        file_size = getattr(media, "file_size", 0)
        is_locked = False

        if hasattr(media, "file_unique_id"):
            file_data = await db.files.find_one({"file_unique_id": media.file_unique_id})
            if file_data:
                if file_data.get("password"): is_locked = True
                if file_data.get("file_name"): file_name = file_data["file_name"]
        
        return {
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"{Config.BASE_URL}/dl/{message_id}",
            "is_locked": is_locked
        }
    except Exception:
        return JSONResponse({"error": "Server Error"}, status_code=500)

@router.post("/api/verify_password")
async def verify_password(data: PasswordCheck):
    try:
        msg = await tg_bot.get_messages(Config.LOG_CHANNEL_ID, data.id)
        if not msg or not msg.media: return {"success": False, "error": "File not found"}
        
        media = msg.document or msg.video or msg.audio
        file_data = await db.files.find_one({"file_unique_id": media.file_unique_id})
        
        if file_data and file_data.get("password") == data.password:
            return {"success": True, "download_url": f"{Config.BASE_URL}/dl/{data.id}?password={data.password}"}
        return {"success": False, "error": "Incorrect Password"}
    except: return {"success": False, "error": "Server Error"}

@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request, password: str = None):
    try:
        msg = await tg_bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        if not msg or not msg.media: raise HTTPException(status_code=404, detail="File not found")
            
        media = msg.document or msg.video or msg.audio
        file_name = getattr(media, "file_name", "file.bin")
        
        if hasattr(media, "file_unique_id"):
            file_data = await db.files.find_one({"file_unique_id": media.file_unique_id})
            if file_data:
                if file_data.get("password") and password != file_data['password']:
                    raise HTTPException(status_code=401, detail="Password Required")
                if file_data.get("file_name"): file_name = file_data["file_name"]

        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        range_header = request.headers.get("range")
        start = 0
        if range_header:
            try: start = int(range_header.replace("bytes=", "").split("-")[0])
            except: pass

        streamer = TgFileStreamer(tg_bot, media.file_id, start_offset=start)
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
        raise HTTPException(status_code=500, detail="Server Error")
