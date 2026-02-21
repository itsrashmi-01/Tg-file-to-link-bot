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

# --- INITIALIZE ROUTER ---
router = APIRouter()
# -------------------------

users_col = db.users
files_col = db.files
auth_codes_col = db.auth_codes

class AuthData(BaseModel):
    initData: str

class FileAction(BaseModel):
    user_id: int
    file_id: str # file_unique_id
    new_name: str = ""

def validate_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = dict(item.split("=", 1) for item in unquote(init_data).split("&"))
        hash_value = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", Config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != hash_value: return None
        return json.loads(parsed_data["user"])
    except: return None

# --- AUTH ENDPOINTS ---
@router.get("/api/auth/generate_token")
async def generate_token():
    token = str(uuid.uuid4())
    await auth_codes_col.insert_one({"token": token, "status": "pending", "timestamp": time.time()})
    try: me = await bot.get_me(); bot_username = me.username
    except: bot_username = "temp_bot"
    return {"token": token, "url": f"https://t.me/{bot_username}?start=login_{token}"}

@router.get("/api/auth/check_token")
async def check_token(token: str):
    data = await auth_codes_col.find_one({"token": token})
    if not data: raise HTTPException(status_code=404, detail="Token expired")
    if data['status'] == 'verified':
        await auth_codes_col.delete_one({"token": token})
        return {"status": "verified", "success": True, "user": data['user_info'], "role": data['role']}
    return {"status": "pending", "success": False}

@router.post("/api/login")
async def login(data: AuthData):
    user = validate_telegram_data(data.initData)
    if not user: raise HTTPException(status_code=401, detail="Invalid Data")
    user_id = user["id"]
    await users_col.update_one({"user_id": user_id}, {"$set": {"first_name": user.get("first_name")}}, upsert=True)
    return {"success": True, "user": user, "role": "admin" if user_id in Config.ADMIN_IDS else "user"}

# --- DASHBOARD & FILE MANAGEMENT ENDPOINTS ---

@router.get("/api/dashboard/user")
async def get_user_dashboard(user_id: int):
    # 1. Calculate Stats (Total Size & Count)
    pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "totalSize": {"$sum": "$file_size"}, "count": {"$sum": 1}}}]
    stats = await files_col.aggregate(pipeline).to_list(1)
    total_size = stats[0]['totalSize'] if stats else 0
    total_count = stats[0]['count'] if stats else 0

    # 2. Fetch Recent Files
    cursor = files_col.find({"user_id": user_id}).sort("_id", -1).limit(50)
    files = []
    async for doc in cursor:
        files.append({
            "file_unique_id": doc.get("file_unique_id"),
            "file_name": doc.get("file_name", "Unknown"),
            "file_size": doc.get("file_size", 0),
            "link": f"{Config.BASE_URL}/dl/{doc.get('log_msg_id')}"
        })
        
    return {"files": files, "stats": {"used_storage": total_size, "total_files": total_count}}

@router.get("/api/search")
async def search_files(user_id: int, query: str):
    # Case-insensitive search
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
        # Optional: Delete from Log Channel
        try: await bot.delete_messages(Config.LOG_CHANNEL_ID, doc['log_msg_id'])
        except: pass
        
        await files_col.delete_one({"_id": doc['_id']})
        return {"success": True}
    return {"success": False}

@router.get("/api/dashboard/admin")
async def get_admin_dashboard(user_id: int):
    if user_id not in Config.ADMIN_IDS: raise HTTPException(status_code=403)
    return {"stats": {"total_users": await users_col.count_documents({}), "total_files": await files_col.count_documents({})}}
