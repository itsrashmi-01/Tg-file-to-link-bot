import time
import hmac
import hashlib
import sys
import os
from fastapi import APIRouter, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES, clones_col

router = APIRouter()
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
files_col = db.large_files
users_col = db.users  # Assuming you have a users collection

SECRET_KEY = Config.API_HASH 

# --- 1. USER APIs (Dashboard, Files, Profile) ---

@router.get("/api/profile/{user_id}")
async def get_user_profile(user_id: int):
    """Get User Stats & Plan Info"""
    user = await users_col.find_one({"_id": user_id})
    if not user:
        # Create default if not exists
        user = {"_id": user_id, "plan": "Free", "points": 0, "created_at": time.time()}
        await users_col.insert_one(user)

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
async def delete_file(unique_id: str, user_id: int = Body(..., embed=True)):
    """Delete a file"""
    result = await files_col.delete_one({"unique_id": unique_id, "user_id": user_id})
    if result.deleted_count > 0:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "error": "File not found"}, status_code=404)

@router.post("/api/upgrade")
async def generate_payment_link(payload: dict = Body(...)):
    """Generate UPI Link"""
    plan = payload.get("plan")
    amount = "199" if plan == "Pro" else "99"
    # Basic UPI Link Format
    upi_link = f"upi://pay?pa={Config.UPI_ID}&pn=BotService&am={amount}&cu=INR"
    return JSONResponse({"upi_link": upi_link, "qr_code": f"https://api.qrserver.com/v1/create-qr-code/?data={upi_link}"})

# --- 2. ADMIN APIs (Stats, Ban, Clones) ---

@router.post("/api/admin/login")
async def admin_login(payload: dict = Body(...)):
    if payload.get("password") == Config.ADMIN_PASSWORD:
        return JSONResponse({"success": True, "token": "admin_session_active"})
    return JSONResponse({"success": False}, status_code=401)

@router.get("/api/admin/stats")
async def get_admin_stats():
    total_files = await files_col.count_documents({})
    total_users = await users_col.count_documents({})
    # Mock revenue calculation
    total_revenue = total_users * 10  
    
    return JSONResponse({
        "total_files": total_files,
        "total_users": total_users,
        "revenue": f"₹{total_revenue}",
        "bot_status": "Online",
        "active_clones": len(RUNNING_CLONES)
    })

@router.post("/api/admin/restart")
async def restart_server(payload: dict = Body(...)):
    if payload.get("password") == Config.ADMIN_PASSWORD:
        # Exit process -> Render automatically restarts it
        sys.exit(0) 
    return JSONResponse({"error": "Unauthorized"}, status_code=401)

@router.post("/api/admin/ban")
async def ban_user(payload: dict = Body(...)):
    user_id = int(payload.get("user_id"))
    await users_col.update_one({"_id": user_id}, {"$set": {"banned": True}}, upsert=True)
    return JSONResponse({"success": True, "msg": f"User {user_id} Banned"})

@router.post("/api/admin/broadcast")
async def broadcast_msg(payload: dict = Body(...)):
    msg = payload.get("message")
    count = 0
    async for user in users_col.find():
        try:
            await bot.send_message(user["_id"], msg)
            count += 1
        except: pass
    return JSONResponse({"success": True, "sent_to": count})

@router.get("/api/admin/clones")
async def get_clones():
    clones = []
    # Fetch from memory or DB
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
    # Stop from memory
    if bot_id in RUNNING_CLONES:
        await RUNNING_CLONES[bot_id]["client"].stop()
        del RUNNING_CLONES[bot_id]
    
    # Remove from DB
    await clones_col.delete_one({"bot_id": int(bot_id)})
    return JSONResponse({"success": True})

# --- 3. DOWNLOAD & STREAMING APIs (Existing) ---
# ... (Keep your existing verify_password, get_file_details, and stream_handler code here) ...
# Ensure you copy those from your previous file or I can include them if needed.
