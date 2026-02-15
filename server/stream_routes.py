from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
import logging
import math

router = APIRouter()
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
files_col = db.large_files

# --- Helper Function for File Size ---
def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

# ==================================================================
# 1. API ROUTE (Used by Blogger to get file info)
# ==================================================================
@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    """
    Returns JSON data about the file. 
    Blogger JavaScript calls this to fill in the Title, Size, and Download Link.
    """
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data:
        return JSONResponse({"error": "File not found or link expired"}, status_code=404)

    # Convert raw bytes to readable size (e.g., "1.5 GB")
    readable_size = human_readable_size(file_data.get('file_size', 0))

    return JSONResponse({
        "file_name": file_data.get('file_name', 'Unknown File'),
        "file_size": readable_size,
        "mime_type": file_data.get('mime_type', 'application/octet-stream'),
        # This link points to the Route 2 below
        "download_url": f"{Config.URL}/dl/{unique_id}"
    })

# ==================================================================
# 2. STREAM ROUTE (The actual download logic)
# ==================================================================
@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request):
    """
    Streams the file from Telegram to the user's browser.
    Supports 'Range' headers for video seeking.
    """
    # A. Find file in DB
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    # B. Get the Message Object from Log Channel
    # We fetch the message fresh to get a valid file_id (they expire over time)
    try:
        msg = await bot.get_messages(Config.LOG_CHANNEL, file_data['message_id'])
        media = msg.document or msg.video or msg.audio
        if not media:
            raise Exception("Message found but contains no media.")
    except Exception as e:
        logging.error(f"Failed to fetch message for {unique_id}: {e}")
        raise HTTPException(status_code=500, detail="File lost in Telegram Log Channel")

    # C. Setup Headers for Browser (Range support allows seeking!)
    file_size = file_data['file_size']
    range_header = request.headers.get("Range")
    
    start, end = 0, file_size - 1
    if range_header:
        # Parse range header "bytes=100-200"
        try:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0]) if parts[0] else 0
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
        except ValueError:
            pass # Fallback to default start/end if header is malformed

    # D. Start Streaming
    # We pass the bot client and the file_id to our custom streamer
    return StreamingResponse(
        TgFileStreamer(bot, media.file_id, start_offset=start),
        status_code=206 if range_header else 200,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": file_data['mime_type'],
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'
        }
    )

# ==================================================================
# 3. HEALTH CHECK (Keeps Render Happy)
# ==================================================================
@router.get("/")
async def health_check():
    return {"status": "Running", "server": "Blogger-Backend-Mode"}
