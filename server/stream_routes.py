import time
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
files_col = db.large_files

SECRET_KEY = Config.API_HASH 
LINK_EXPIRY = 3600 

# --- HELPER: Generate Secure Cloudflare Link ---
def create_secure_link(unique_id):
    expires = int(time.time()) + LINK_EXPIRY
    signature = hmac.new(SECRET_KEY.encode(), f"{unique_id}{expires}".encode(), hashlib.sha256).hexdigest()
    return f"{Config.URL}/dl/{unique_id}?token={signature}&expires={expires}"

# --- API: Get File Info (Called on Page Load) ---
@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data: return JSONResponse({"error": "File not found"}, status_code=404)

    # Check if Password Exists
    is_locked = bool(file_data.get("password"))

    response = {
        "file_name": file_data.get('file_name', 'Unknown'),
        "file_size": file_data.get('file_size', 0),
        "is_locked": is_locked  # Tell frontend it's locked
    }

    # If NOT locked, give the link immediately
    if not is_locked:
        response["download_url"] = create_secure_link(unique_id)
    
    return JSONResponse(response)

# --- API: Verify Password (Called when user types password) ---
@router.post("/api/verify_password")
async def verify_password(payload: dict = Body(...)):
    unique_id = payload.get("id")
    user_pass = payload.get("password")

    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data: return JSONResponse({"error": "File not found"}, status_code=404)

    correct_pass = file_data.get("password")

    if user_pass == correct_pass:
        return JSONResponse({
            "success": True,
            "download_url": create_secure_link(unique_id)
        })
    else:
        return JSONResponse({"success": False, "error": "❌ Wrong Password"}, status_code=401)

# --- API: Stream File (The Download) ---
@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request, token: str = Query(None), expires: int = Query(None)):
    # 1. Security Checks
    message = f"{unique_id}{expires}"
    expected = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected, token or "") or int(time.time()) > int(expires or 0):
        raise HTTPException(status_code=403, detail="❌ Link Expired or Invalid")

    # 2. Get File Data
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data: raise HTTPException(status_code=404, detail="File not found")

    # 3. Select Client (Main or Clone)
    owner_bot_id = file_data.get("bot_id")
    if owner_bot_id and owner_bot_id in RUNNING_CLONES:
        active_client = RUNNING_CLONES[owner_bot_id]["client"]
        target_channel = RUNNING_CLONES[owner_bot_id]["log_channel"]
    else:
        active_client = bot
        target_channel = int(Config.LOG_CHANNEL)

    try:
        msg = await active_client.get_messages(target_channel, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        
        # 4. Stream with Range Support
        streamer = TgFileStreamer(
            active_client, media.file_id, file_data['file_size'], request.headers.get("range")
        )
        response_size = (streamer.end - streamer.start) + 1
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(response_size),
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
        }
        
        status_code = 206 if request.headers.get("range") else 200
        if status_code == 206:
            headers["Content-Range"] = f"bytes {streamer.start}-{streamer.end}/{file_data['file_size']}"

        return StreamingResponse(streamer, status_code=status_code, media_type=file_data['mime_type'], headers=headers)

    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="File Stream Failed")
