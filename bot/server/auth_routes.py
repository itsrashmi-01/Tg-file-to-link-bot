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
from bot_client import tg_bot 

router = APIRouter()

users_col = db.users
files_col = db.files
auth_codes_col = db.auth_codes
clones_col = db.clones

class AuthData(BaseModel):
    initData: str
    bot_id: str = None 

class FileAction(BaseModel):
    user_id: int
    file_id: str
    new_name: str = ""

# --- HELPERS ---
async def get_bot_token(bot_id: str):
    main_bot_id = Config.BOT_TOKEN.split(":")[0]
    if not bot_id or bot_id == main_bot_id: return Config.BOT_TOKEN
    try:
        clone = await clones_col.find_one({"token": {"$regex": f"^{bot_id}:"}})
        if clone: return clone['token']
    except: pass
    return Config.BOT_TOKEN 

async def validate_telegram_data(init_data: str, bot_token: str) -> dict:
    try:
        parsed_data = dict(item.split("=", 1) for item in unquote(init_data).split("&"))
        hash_value = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != hash_value: return None
        return json.loads(parsed_data["user"])
    except: return None

async def get_user_role(user_id):
    if user_id in Config.ADMIN_IDS: return "admin"
    if await clones_col.find_one({"user_id": user_id}): return "clone_admin"
    return "user"

# --- ROUTES ---

@router.get("/api/auth/generate_token")
async def generate_token():
    token = str(uuid.uuid4())
    await auth_codes_col.insert_one({"token": token, "status": "pending", "timestamp": time.time()})
    try: me = await tg_bot.get_me(); bot_username = me.username
    except: bot_username = "temp_bot"
    return {"token": token, "url": f"https://t.me/{bot_username}?start=login_{token}"}

@router.get("/api/auth/check_token")
async def check_token(token: str):
    data = await auth_codes_col.find_one({"token": token})
    if not data: raise HTTPException(status_code=404, detail="Token expired")
    if data['status'] == 'verified':
        await auth_codes_col.delete_one({"token": token})
        role = await get_user_role(data['user_info']['id'])
        return {"status": "verified", "success": True, "user": data['user_info'], "role": role}
    return {"status": "pending", "success": False}

@router.post("/api/login")
async def login(data: AuthData):
    token_to_use = await get_bot_token(data.bot_id)
    user = await validate_telegram_data(data.initData, token_to_use)
    if not user: raise HTTPException(status_code=401, detail="Invalid Data")
    
    user_id = user["id"]
    await users_col.update_one({"user_id": user_id}, {"$set": {"first_name": user.get("first_name")}}, upsert=True)
    
    role = await get_user_role(user_id)
    return {"success": True, "user": user, "role": role}

@router.get("/api/dashboard/user")
async def get_dashboard(user_id: int):
    # 1. Identify Role
    role = await get_user_role(user_id)
    
    # 2. Common Data (User Files & Usage)
    pipeline = [{"$match": {"user_id": user_id}}, {"$group": {"_id": None, "totalSize": {"$sum": "$file_size"}, "count": {"$sum": 1}}}]
    stats = await files_col.aggregate(pipeline).to_list(1)
    user_stats = {
        "used_storage": stats[0]['totalSize'] if stats else 0,
        "total_files": stats[0]['count'] if stats else 0
    }

    cursor = files_col.find({"user_id": user_id}).sort("_id", -1).limit(50)
    files = []
    async for doc in cursor:
        files.append({
            "file_unique_id": doc.get("file_unique_id"),
            "file_name": doc.get("file_name", "Unknown"),
            "file_size": doc.get("file_size", 0),
            "link": f"{Config.BASE_URL}/dl/{doc.get('log_msg_id')}"
        })

    # 3. Role Specific Data
    admin_data = None
    clone_data = None

    if role == "admin":
        admin_data = {
            "total_users": await users_col.count_documents({}),
            "total_clones": await clones_col.count_documents({}),
            "total_files": await files_col.count_documents({})
        }
    
    if role == "clone_admin":
        clone_doc = await clones_col.find_one({"user_id": user_id})
        if clone_doc:
            clone_data = {
                "username": clone_doc.get("username"),
                "token": clone_doc.get("token")[:10] + "..." # Masked
            }

    return {
        "role": role,
        "stats": user_stats,
        "files": files,
        "admin_data": admin_data,
        "clone_data": clone_data
    }

@router.get("/api/search")
async def search_files(user_id: int, query: str):
    cursor = files_col.find({"user_id": user_id, "file_name": {"$regex": query, "$options": "i"}}).limit(20)
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
    result = await files_col.update_one({"file_unique_id": data.file_id, "user_id": data.user_id}, {"$set": {"file_name": data.new_name}})
    return {"success": result.modified_count > 0}

@router.post("/api/file/delete")
async def delete_file(data: FileAction):
    doc = await files_col.find_one({"file_unique_id": data.file_id, "user_id": data.user_id})
    if doc:
        try: await tg_bot.delete_messages(Config.LOG_CHANNEL_ID, doc['log_msg_id']) 
        except: pass
        await files_col.delete_one({"_id": doc['_id']})
        return {"success": True}
    return {"success": False}

@router.post("/api/clone/delete")
async def delete_clone(data: dict):
    await clones_col.delete_one({"user_id": data.get("user_id")})
    return {"success": True}

@router.get("/api/settings/get")
async def get_settings(user_id: int):
    user = await users_col.find_one({"user_id": user_id})
    return {"use_shortener": user.get("use_short", False) if user else False}

@router.post("/api/settings/update")
async def update_settings(data: dict):
    await users_col.update_one({"user_id": data.get("user_id")}, {"$set": {"use_short": data.get("value")}}, upsert=True)
    return {"success": True}
