from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from bot_client import bot
from bot.utils import TgFileStreamer

router = APIRouter()

# --- 1. API Endpoint (Used by Blogger to get File Info) ---
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
        
        # Return JSON data for the Blogger script
        return {
            "file_name": file_name,
            "file_size": file_size,
            "download_url": f"{Config.BASE_URL}/dl/{message_id}",
            "is_locked": False # Password feature can be added later
        }

    except Exception as e:
        print(f"API Error: {e}")
        return JSONResponse({"error": "Server Error"}, status_code=500)


# --- 2. Download Endpoint (The Actual Stream) ---
@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request):
    try:
        msg = await bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="File not found")
            
        media = msg.document or msg.video or msg.audio
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
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Server Error")
