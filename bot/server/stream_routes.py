from fastapi import APIRouter, Request, HTTPException, Query
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
    user_id: int

# --- HELPER: Get Client and Channel ---
async def get_client_and_channel(message_id: int, user_id: int = None):
    """
    Finds the correct Pyrogram client and channel ID for a given message.
    """
    # 1. Select the client (Clone or Main)
    client = CLONE_BOTS.get(user_id, tg_bot) if user_id else tg_bot
    
    # 2. Find file in DB to get the specific channel
    # This allows users to use their OWN log channels
    file_data = await files_col.find_one({"log_msg_id": message_id})
    if not file_data:
        return None, None, None
    
    channel_id = file_data.get("log_channel", Config.LOG_CHANNEL_ID)
    return client, channel_id, file_data

# --- ROUTES ---

@router.get("/api/file/{message_id}")
async def get_file_info(message_id: int, user_id: int = Query(None)):
    try:
        client, channel_id, file_data = await get_client_and_channel(message_id, user_id)
        if not client:
            return JSONResponse({"error": "File not found in DB"}, status_code=404)

        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            return JSONResponse({"error": "File not found on Telegram"}, status_code=404)
            
        media = msg.document or msg.video or msg.audio
        
        return {
            "file_name": file_data.get("file_name", getattr(media, "file_name", "file")),
            "file_size": getattr(media, "file_size", 0),
            "download_url": f"{Config.BASE_URL}/dl/{message_id}?user_id={user_id}" if user_id else f"{Config.BASE_URL}/dl/{message_id}",
            "is_locked": bool(file_data.get("password"))
        }
    except Exception as e:
        print(f"API Info Error: {e}")
        return JSONResponse({"error": "Server Error"}, status_code=500)

@router.post("/api/verify_password")
async def verify_password(data: PasswordCheck):
    try:
        _, _, file_data = await get_client_and_channel(data.id, data.user_id)
        
        if file_data and file_data.get("password") == data.password:
            return {
                "success": True, 
                "download_url": f"{Config.BASE_URL}/dl/{data.id}?user_id={data.user_id}&password={data.password}"
            }
        
        return {"success": False, "error": "Incorrect Password"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/dl/{message_id}")
async def stream_file(message_id: int, request: Request, user_id: int = Query(None), password: str = None):
    try:
        client, channel_id, file_data = await get_client_and_channel(message_id, user_id)
        if not client:
            raise HTTPException(status_code=404, detail="File metadata not found")

        # Password Protection Check
        if file_data.get("password") and password != file_data['password']:
            raise HTTPException(status_code=401, detail="Password Required")

        msg = await client.get_messages(channel_id, message_id)
        if not msg or not msg.media:
            raise HTTPException(status_code=404, detail="File not found on Telegram")
            
        media = msg.document or msg.video or msg.audio
        file_size = getattr(media, "file_size", 0)
        file_name = file_data.get("file_name", getattr(media, "file_name", "file"))
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        # Handle Range Requests for Streaming
        range_header = request.headers.get("range")
        start = 0
        end = file_size - 1
        
        if range_header:
            try:
                # bytes=start-end
                range_value = range_header.replace("bytes=", "").split("-")
                start = int(range_value[0])
                if range_value[1]:
                    end = int(range_value[1])
            except:
                pass

        streamer = TgFileStreamer(client, media.file_id, start_offset=start)
        
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
        }

        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        return StreamingResponse(
            streamer, 
            status_code=206 if range_header else 200, 
            headers=headers, 
            media_type=mime_type
        )
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
