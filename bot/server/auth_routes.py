import hashlib
import hmac
import json
import uuid
import time
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import Config
from bot.clone import db
from bot_client import bot

# --- 1. INITIALIZE ROUTER FIRST ---
router = APIRouter()
# ----------------------------------

users_col = db.users
files_col = db.files
auth_codes_col = db.auth_codes

class AuthData(BaseModel):
    initData: str

def validate_telegram_data(init_data: str) -> dict:
    """Validates the initData string sent by Telegram Web App."""
    try:
        parsed_data = dict(item.split("=", 1) for item in unquote(init_data).split("&"))
        hash_value = parsed_data.pop("hash")
        
        # Sort keys alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # HMAC Calculation
        secret_key = hmac.new(b"WebAppData", Config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_value:
            raise ValueError("Invalid Hash")
            
        return json.loads(parsed_data["user"])
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

# --- NEW: Generate Login Link ---
@router.get("/api/auth/generate_token")
async def generate_token():
    token = str(uuid.uuid4())
    
    # Store token in DB with "pending" status
    await auth_codes_col.insert_one({
        "token": token,
        "status": "pending",
        "timestamp": time.time()
    })
    
    # Get Bot Username dynamically
    try:
        me = await bot.get_me()
        bot_username = me.username
    except:
        bot_username = "temp_bot"

    return {
        "token": token,
        "url": f"https://t.me/{bot_username}?start=login_{token}"
    }

# --- NEW: Check Login Status (Polling) ---
@router.get("/api/auth/check_token")
async def check_token(token: str):
    data = await auth_codes_col.find_one({"token": token})
    
    if not data:
        raise HTTPException(status_code=404, detail="Token not found or expired")
    
    if data['status'] == 'verified':
        # Login Successful! Return user data and clean up token
        await auth_codes_col.delete_one({"token": token})
        return {
            "status": "verified",
            "success": True,
            "user": data['user_info'],
            "role": data['role']
        }
    
    return {"status": "pending", "success": False}

@router.post("/api/login")
async def login(data: AuthData):
    user = validate_telegram_data(data.initData)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Telegram Data")
    
    user_id = user["id"]
    is_admin = user_id in Config.ADMIN_IDS
    
    # Save/Update User in DB
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": user.get("first_name"), "username": user.get("username")}},
        upsert=True
    )

    return {
        "success": True,
        "user": user,
        "role": "admin" if is_admin else "user"
    }

@router.get("/api/dashboard/user")
async def get_user_dashboard(user_id: int):
    # Fetch last 50 files uploaded by this user
    cursor = files_col.find({"user_id": user_id}).sort("_id", -1).limit(50)
    files = []
    async for doc in cursor:
        files.append({
            "file_name": doc.get("file_name", "Unknown"),
            "file_size": doc.get("file_size", 0),
            "link": f"{Config.BASE_URL}/dl/{doc.get('log_msg_id')}"
        })
    return {"files": files}

@router.get("/api/dashboard/admin")
async def get_admin_dashboard(user_id: int):
    # Security check: Ensure requester is actually an admin
    if user_id not in Config.ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Not Authorized")
        
    total_users = await users_col.count_documents({})
    total_files = await files_col.count_documents({})
    
    return {
        "stats": {
            "total_users": total_users,
            "total_files": total_files
        }
    }
