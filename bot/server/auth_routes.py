import uuid
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bot.clone import db
from bot_client import bot 
from config import Config

# ... (Keep existing imports and router definition) ...

auth_codes_col = db.auth_codes # New collection for temporary login codes

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
        bot_username = "temp_bot" # Should not happen if bot is running

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
