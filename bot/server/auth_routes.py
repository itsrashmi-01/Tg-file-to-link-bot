import hashlib
import hmac
import json
import uuid
import time
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import Config
from bot.clone import db, stop_clone
from bot_client import tg_bot 

router = APIRouter()

# Database Collections
users_col = db.users
files_col = db.files
auth_codes_col = db.auth_codes
clones_col = db.clones

class AuthData(BaseModel):
    initData: str

class FileAction(BaseModel):
    user_id: int
    file_id: str
    new_name: str = ""

# --- VALIDATION HELPER (Dynamic Token Fix) ---
async def validate_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = dict(item.split("=", 1) for item in unquote(init_data).split("&"))
        hash_value = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Extract user info to get the user_id
        user_json = json.loads(parsed_data["user"])
        user_id = user_json.get("id")

        # 1. Determine which token to use for verification
        # Check if the user is a clone owner
        clone = await clones_col.find_one({"user_id": user_id})
        bot_token = clone["token"] if clone else Config.BOT_TOKEN

        # 2. Verify HMAC
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != hash_value: 
            return None
            
        return user_json
    except Exception as e:
        print(f"Auth Validation Error: {e}")
        return None

# --- AUTH ROUTES ---
@router.get("/api/auth/generate_token")
async def generate_token():
    token = str(uuid.uuid4())
    await auth_codes_col.insert_one({
        "token": token, 
        "status": "pending", 
        "timestamp": time.time()
    })
    try: 
        me = await tg_bot.get_me() 
        bot_username = me.username
    except: 
        bot_username = "temp_bot"
    return {"token": token, "url": f"https://t.me/{bot_username}?start=login_{token}"}

@router.get("/api/auth/check_token")
async def check_token(token: str):
    data = await auth_codes_col.find_one({"token": token})
    if not data: 
        raise HTTPException(status_code=404, detail="Token expired")
    
    if data['status'] == 'verified':
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
    # Pass to the async validator
    user = await validate_telegram_data(data.initData)
    if not user: 
        raise HTTPException(status_code=401, detail="Invalid Data or Unauthorized Bot")
    
    user_id = user["id"]
    await users_col.update_one(
        {"user_id": user_id}, 
        {"$set": {"first_name": user.get("first_name"), "last_seen": time.time()}}, 
        upsert=True
    )
    return {
        "success": True, 
        "user": user, 
        "role": "admin" if user_id in Config.ADMIN_IDS else "user"
    }

# --- DASHBOARD ROUTES ---
@router.get("/api/dashboard/user")
async def get_user_dashboard(user_id: int):
    # 1. Stats
    pipeline = [
        {"$match": {"user_id": user_id}}, 
        {"$group": {"_id": None, "totalSize": {"$sum": "$file_size"}, "count": {"$sum": 1}}}
    ]
    cursor = files_col.aggregate(pipeline)
    stats_list = await cursor.to_list(length=1)
    
    total_size = stats_list[0]['totalSize'] if stats_list else 0
    total_count = stats_list[0]['count'] if stats_list else 0

    # 2. Files
    cursor = files_col.find({"user_id": user_id}).sort("_id", -1).limit(50)
    files = []
    async for doc in cursor:
        files.append({
            "file_unique_id": doc.get("file_unique_id"),
            "file_name": doc.get("file_name", "Unknown"),
            "file_size": doc.get("file_size", 0),
            "link": f"{Config.BASE_URL}/dl/{doc.get('log_msg_id')}"
        })
        
    # 3. Clone Bot Info
    clone_info = await clones_col.find_one({"user_id": user_id})
    clone_data = None
    if clone_info:
        clone_data = {
            "username": clone_info.get("username"),
        }
        
    return {
        "files": files, 
        "stats": {"used_storage": total_size, "total_files": total_count},
        "clone_bot": clone_data
    }

@router.get("/api/search")
async def search_files(user_id: int, query: str):
    cursor = files_col.find({
        "user_id": user_id,
        "file_name": {"$regex": query, "$options": "i"}
    }).limit(20)
    
    files = []
    async for doc in cursor:
        files.append({
            "file_unique_id": doc.get("file_unique_id"),
            "file_name": doc.get("file_name", "Unknown"),
            "file_size": doc.get("file_size", 0),
            "link": f"{Config.BASE_URL}/dl/{doc.get('log_msg_id')}"
        })
    return {"files": files}

# --- FILE ACTIONS ---
@router.post("/api/file/rename")
async def rename_file(data: FileAction):
    result = await files_col.update_one(
        {"file_unique_id": data.file_id, "user_id": data.user_id},
        {"$set": {"file_name": data.new_name}}
    )
    return {"success": result.modified_count > 0}

@router.post("/api/file/delete")
async def delete_file(data: FileAction):
    doc = await files_col.find_one({"file_unique_id": data.file_id, "user_id": data.user_id})
    if doc:
        # Note: Deleting from Telegram log is handled as best-effort
        try: 
            # Check if it was in the main log channel
            if doc.get('channel_id') == Config.LOG_CHANNEL_ID:
                await tg_bot.delete_messages(Config.LOG_CHANNEL_ID, doc['log_msg_id']) 
        except: pass
        
        await files_col.delete_one({"_id": doc['_id']})
        return {"success": True}
    return {"success": False}

# --- CLONE ACTIONS ---
@router.post("/api/clone/delete")
async def delete_clone_api(data: dict):
    user_id = data.get("user_id")
    # Stop running bot instance
    await stop_clone(user_id)
    # Remove from DB
    await clones_col.delete_one({"user_id": user_id})
    return {"success": True}

# --- SETTINGS ---
@router.get("/api/settings/get")
async def get_settings(user_id: int):
    user = await users_col.find_one({"user_id": user_id})
    if user: return {"use_shortener": user.get("use_short", False)}
    return {"use_shortener": False}

@router.post("/api/settings/update")
async def update_settings(data: dict):
    key_map = {"use_shortener": "use_short"}
    setting = data.get("setting")
    if setting in key_map:
        db_key = key_map[setting]
        await users_col.update_one(
            {"user_id": data.get("user_id")},
            {"$set": {db_key: data.get("value")}},
            upsert=True
        )
        return {"success": True}
    return {"success": False}
