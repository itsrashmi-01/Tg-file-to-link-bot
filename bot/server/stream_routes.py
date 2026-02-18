from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from config import Config
from bot_client import bot
from bot.utils import TgFileStreamer

router = APIRouter()

@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request):
    try:
        # Fetch Message from Log Channel
        msg = await bot.get_messages(Config.LOG_CHANNEL_ID, message_id)
        
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="File not found")
            
        media = msg.document or msg.video or msg.audio
        file_name = getattr(media, "file_name", "file.bin")
        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        # Handle Range Requests (Required for video seeking)
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