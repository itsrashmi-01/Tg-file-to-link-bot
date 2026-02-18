import time
import hmac
import hashlib
import json
import sys
from urllib.parse import parse_qsl
from fastapi import APIRouter, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from bot.utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES, clones_col

router = APIRouter()

# --- DATABASE CONNECTION ---
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
files_col = db.large_files
users_col = db.users

SECRET_KEY = Config.API_HASH 

# ==================================================================
# 1. AUTHENTICATION HELPER (TELEGRAM MINI APP)
# ==================================================================
def validate_telegram_data(init_data: str) -> dict:
    """
    Validates the initData received from Telegram Web App.
    Returns the User Data object if valid, otherwise None.
    """
    try:
        if not init_data: return None
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data: return None

        received_hash = parsed_data.pop("hash")
        
        # Sort keys alphabetically to create the data-check-string
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Calculate Secret Key (HMAC-SHA256 of Bot Token)
        secret_key = hmac.new(b"WebAppData", Config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Calculate Signature
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == received_hash:
            return json.loads(parsed_data["user"])
        return None
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

# ==================================================================
# 2. AUTH ROUTES
# ==================================================================

@router.post("/api/auth/telegram")
async def telegram_auth(payload: dict = Body(...)):
    """Auto-Login for Telegram Mini App Users"""
    user_data = validate_telegram_data(payload.get("init_data"))
    
    if not user_data:
        return JSONResponse({"success": False, "error": "Invalid Data"}, status_code=403)

    user_id = user_data["id"]
    
    # Check/Create User in DB
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, 
            "first_name": user_data.get("first_name", "User"),
            "plan": "Free", 
            "points": 0, 
            "created_at": time.time()
        }
        await users_col.insert_one(user)

    return JSONResponse({
        "success": True,
        "user_id": user_id,
        "name": user.get("first_name"),
        "plan": user.get("plan")
    })

@router.post("/api/admin/login")
async def admin_login(payload: dict = Body(...)):
    """Manual Admin Password Login"""
    if payload.get("password") == Config.ADMIN_PASSWORD:
        return JSONResponse({"success": True, "token": "admin_session_active"})
    return JSONResponse({"success": False, "error": "Wrong Password"}, status_code=401)

# ==================================================================
# 3. USER DASHBOARD APIs
# ==================================================================

@router.get("/api/profile/{user_id}")
async def get_user_profile(user_id: int):
    """Get User Stats & Plan Info"""
    user = await users_col.find_one({"_id": user_id})
    if not user:
        # Return default info for non-db users
        return JSONResponse({"name": "Guest", "plan": "Free", "total_files": 0, "referral_points": 0})

    file_count = await files_col.count_documents({"user_id": user_id})
    
    return JSONResponse({
        "name": user.get("first_name", "User"),
        "plan": user.get("plan", "Free"),
        "total_files": file_count,
        "referral_points": user.get("points", 0)
    })

@router.get("/api/files/{user_id}")
async def list_user_files(user_id: int, limit: int = 50):
    """List specific user's files"""
    cursor = files_col.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    files = []
    async for f in cursor:
        files.append({
            "unique_id": f.get("unique_id"),
            "name": f.get("file_name"),
            "size": f.get("file_size"),
            "views": f.get("views", 0)
        })
    return JSONResponse({"files": files})

@router.delete("/api/file/{unique_id}")
async def delete_file(unique_id: str, payload: dict = Body(...)):
    """Delete a file owned by the user"""
    user_id = int(payload.get("user_id"))
    result = await files_col.delete_one({"unique_id": unique_id, "user_id": user_id})
    
    if result.deleted_count > 0:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "error": "File not found or access denied"}, status_code=404)

@router.post("/api/upgrade")
async def generate_payment_link(payload: dict = Body(...)):
    """Generate UPI Payment Link"""
    plan = payload.get("plan")
    # Default prices
    amount = "199" if plan == "Pro" else "99"
    
    # Check if UPI ID is configured
    upi_id = getattr(Config, 'UPI_ID', 'your-upi-id@okhdfcbank')
    
    upi_link = f"upi://pay?pa={upi_id}&pn=BotService&am={amount}&cu=INR"
    qr_code = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={upi_link}"
    
    return JSONResponse({"upi_link": upi_link, "qr_code": qr_code})

# ==================================================================
# 4. ADMIN PANEL APIs
# ==================================================================

@router.get("/api/admin/stats")
async def get_admin_stats():
    """Global Stats for Admin Dashboard"""
    total_files = await files_col.count_documents({})
    total_users = await users_col.count_documents({})
    
    # Calculate Total Views
    pipeline = [{"$group": {"_id": None, "total_views": {"$sum": "$views"}}}]
    cursor = files_col.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    total_views = result[0]["total_views"] if result else 0

    return JSONResponse({
        "total_files": total_files,
        "total_users": total_users,
        "revenue": f"₹{total_users * 10}",  # Mock Revenue
        "total_views": total_views,
        "active_clones": len(RUNNING_CLONES)
    })

@router.post("/api/admin/restart")
async def restart_server(payload: dict = Body(...)):
    """Restart the Render Service"""
    if payload.get("password") == Config.ADMIN_PASSWORD:
        sys.exit(0) # Render will auto-restart the process
    return JSONResponse({"error": "Unauthorized"}, status_code=401)

@router.post("/api/admin/ban")
async def ban_user(payload: dict = Body(...)):
    """Ban a user"""
    try:
        user_id = int(payload.get("user_id"))
        await users_col.update_one({"_id": user_id}, {"$set": {"banned": True}}, upsert=True)
        return JSONResponse({"success": True, "msg": f"User {user_id} Banned"})
    except:
        return JSONResponse({"success": False, "error": "Invalid ID"})

@router.post("/api/admin/broadcast")
async def broadcast_msg(payload: dict = Body(...)):
    """Send message to all users"""
    msg = payload.get("message")
    count = 0
    async for user in users_col.find():
        try:
            await bot.send_message(user["_id"], msg)
            count += 1
            if count % 20 == 0: await asyncio.sleep(1) # Flood control
        except: pass
    return JSONResponse({"success": True, "sent_to": count})

@router.get("/api/admin/clones")
async def get_clones():
    """List all clone bots"""
    clones = []
    async for c in clones_col.find():
        status = "Running" if c.get("bot_id") in RUNNING_CLONES else "Stopped"
        clones.append({
            "bot_id": c.get("bot_id"),
            "username": c.get("username"),
            "status": status
        })
    return JSONResponse({"clones": clones})

@router.delete("/api/admin/clone/{bot_id}")
async def delete_clone(bot_id: int):
    """Stop and Delete a Clone"""
    if bot_id in RUNNING_CLONES:
        try:
            await RUNNING_CLONES[bot_id].stop()
            del RUNNING_CLONES[bot_id]
        except: pass
    
    await clones_col.delete_one({"bot_id": int(bot_id)})
    return JSONResponse({"success": True})

# ==================================================================
# 5. PUBLIC DOWNLOAD & STREAMING APIs
# ==================================================================

@router.get("/api/file/{unique_id}")
async def get_file_details(unique_id: str):
    """Public File Info for Download Page"""
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data: return JSONResponse({"error": "File not found"}, status_code=404)

    is_locked = bool(file_data.get("password"))
    
    # Helper to generate signed link
    def create_link():
        expires = int(time.time()) + 3600 # 1 Hour link
        sig = hmac.new(SECRET_KEY.encode(), f"{unique_id}{expires}".encode(), hashlib.sha256).hexdigest()
        return f"{Config.BASE_URL}/dl/{unique_id}?token={sig}&expires={expires}"

    response = {
        "file_name": file_data.get('file_name', 'Unknown'),
        "file_size": file_data.get('file_size', 0),
        "is_locked": is_locked,
        "views": file_data.get("views", 0)
    }

    if not is_locked:
        response["download_url"] = create_link()
    
    return JSONResponse(response)

@router.post("/api/verify_password")
async def verify_password(payload: dict = Body(...)):
    """Verify password for locked files"""
    unique_id = payload.get("id")
    user_pass = payload.get("password")
    
    file_data = await files_col.find_one({"unique_id": unique_id})
    
    if file_data and file_data.get("password") == user_pass:
        expires = int(time.time()) + 3600
        sig = hmac.new(SECRET_KEY.encode(), f"{unique_id}{expires}".encode(), hashlib.sha256).hexdigest()
        dl_url = f"{Config.BASE_URL}/dl/{unique_id}?token={sig}&expires={expires}"
        return JSONResponse({"success": True, "download_url": dl_url})
        
    return JSONResponse({"success": False, "error": "Wrong Password"}, status_code=401)

@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request, token: str = Query(None), expires: int = Query(None)):
    """
    The Main Streaming Endpoint.
    Handles Range Requests (Seeking), View Counting, and Security.
    """
    # 1. Security Check
    expected = hmac.new(SECRET_KEY.encode(), f"{unique_id}{expires}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token or "") or int(time.time()) > int(expires or 0):
        raise HTTPException(status_code=403, detail="Link Expired")

    # 2. Get File Info
    file_data = await files_col.find_one({"unique_id": unique_id})
    if not file_data: raise HTTPException(status_code=404, detail="File not found")

    # 3. Increment Views (Async update)
    await files_col.update_one({"unique_id": unique_id}, {"$inc": {"views": 1}})

    # 4. Select Client (Main Bot or Clone)
    owner_id = file_data.get("bot_id")
    # If file belongs to a clone and clone is running, use it. Else use main bot.
    if owner_id and owner_id in RUNNING_CLONES:
        client = RUNNING_CLONES[owner_id]
        channel = RUNNING_CLONES[owner_id].log_channel_id if hasattr(RUNNING_CLONES[owner_id], 'log_channel_id') else Config.LOG_CHANNEL_ID
        # Note: Clones usually forward to Main Log Channel, so we default to Config.LOG_CHANNEL_ID
        # If your clones use separate channels, you need to store that in DB.
        # Assuming all forward to MAIN LOG CHANNEL for now:
        channel = Config.LOG_CHANNEL_ID 
    else:
        client = bot
        channel = Config.LOG_CHANNEL_ID

    try:
        # 5. Fetch Message from Telegram
        msg = await client.get_messages(channel, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        
        # 6. Handle Range Header (Video Seeking)
        range_header = request.headers.get("range")
        start, end = 0, media.file_size - 1
        if range_header:
            start = int(range_header.replace("bytes=", "").split("-")[0])

        # 7. Start Stream
        streamer = TgFileStreamer(client, media.file_id, start_offset=start)
        
        headers = {
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(media.file_size - start)
        }
        
        return StreamingResponse(
            streamer, 
            status_code=206 if range_header else 200, 
            headers=headers, 
            media_type=file_data['mime_type']
        )
    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Stream Failed")
