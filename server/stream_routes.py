import time, hmac, hashlib, datetime
from fastapi import APIRouter, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from utils import TgFileStreamer
from bot_client import bot
from bot.clone import RUNNING_CLONES

router = APIRouter()

# DUAL DB
main_client = AsyncIOMotorClient(Config.MONGO_URL)
main_db = main_client.TelegramBotCluster
clone_client = AsyncIOMotorClient(Config.CLONE_MONGO_URL)
clone_db = clone_client.CloneBotCluster
users_col = main_db.large_file_users

SECRET = Config.API_HASH

async def find_file(uid):
    f = await main_db.large_files.find_one({"unique_id": uid})
    if f: return f
    return await clone_db.large_files.find_one({"unique_id": uid})

def secure_link(uid):
    exp = int(time.time()) + 3600
    sig = hmac.new(SECRET.encode(), f"{uid}{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{Config.URL}/dl/{uid}?token={sig}&expires={exp}"

@router.get("/api/file/{uid}")
async def get_info(uid: str):
    file = await find_file(uid)
    if not file: return JSONResponse({"error": "Not Found"}, 404)
    
    user = await users_col.find_one({"_id": file["user_id"]})
    is_prem = False
    if user and user.get("plan_type") == "premium":
        if user.get("plan_expiry") and user["plan_expiry"] > datetime.datetime.now(): is_prem = True
    
    res = {
        "file_name": file.get('file_name'), "file_size": file.get('file_size'),
        "is_locked": bool(file.get("password")), "show_ads": not is_prem
    }
    if not res["is_locked"]: res["download_url"] = secure_link(uid)
    return JSONResponse(res)

@router.post("/api/verify_password")
async def verify(payload: dict = Body(...)):
    uid = payload.get("id")
    file = await find_file(uid)
    if not file: return JSONResponse({"error": "Not Found"}, 404)
    
    if payload.get("password") == file.get("password"):
        return JSONResponse({"success": True, "download_url": secure_link(uid)})
    return JSONResponse({"success": False, "error": "Wrong Password"}, 401)

@router.get("/dl/{uid}")
async def stream(uid: str, request: Request, token: str = Query(None), expires: int = Query(None)):
    msg = f"{uid}{expires}"
    expected = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token or "") or int(time.time()) > int(expires or 0):
        raise HTTPException(403, "Link Expired")
        
    file = await find_file(uid)
    if not file: raise HTTPException(404, "File Not Found")
    
    bid = file.get("bot_id")
    if bid and bid in RUNNING_CLONES:
        client = RUNNING_CLONES[bid]["client"]
        chan = int(RUNNING_CLONES[bid]["log_channel"])
    else:
        client = bot
        chan = int(Config.LOG_CHANNEL)
    
    try:
        try: await client.get_chat(chan)
        except: pass
        
        tg_msg = await client.get_messages(chan, int(file['message_id']))
        media = tg_msg.document or tg_msg.video or tg_msg.audio
        
        streamer = TgFileStreamer(client, media.file_id, file['file_size'], request.headers.get("range"))
        size = (streamer.end - streamer.start) + 1
        
        headers = {
            "Accept-Ranges": "bytes", "Content-Length": str(size),
            "Content-Disposition": f'attachment; filename="{file["file_name"]}"'
        }
        code = 206 if request.headers.get("range") else 200
        if code == 206: headers["Content-Range"] = f"bytes {streamer.start}-{streamer.end}/{file['file_size']}"
        
        return StreamingResponse(streamer, status_code=code, media_type=file['mime_type'], headers=headers)
    except Exception as e:
        print(e)
        raise HTTPException(500, "Stream Failed")