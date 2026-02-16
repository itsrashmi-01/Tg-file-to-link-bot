import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

# --- THE FIX: DIRECT PYROGRAM IMPORT ---
try:
    from pyrogram import Client
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyrogram", "tgcrypto"])
    from pyrogram import Client

# Local Imports
from config import Config
from database.files import file_db
from bot import bot_client  # Ensure bot/__init__.py has bot_client = Client(...)

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    try:
        if bot_client:
            await bot_client.start()
            print(f"✅ Bot Started Successfully: @{bot_client.me.username}")
        else:
            print("❌ bot_client instance is missing!")
    except Exception as e:
        print(f"❌ Critical Error during Bot Startup: {e}")
    
    yield  # Web Server is active now
    
    print("😴 Shutting down...")
    try:
        if bot_client and bot_client.is_connected:
            await bot_client.stop()
    except:
        pass

# --- FastAPI Setup ---
app = FastAPI(title="Pro File Link Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/")
async def health():
    return {"status": "online", "bot_ready": bot_client.is_connected if bot_client else False}

@app.get("/api/info/{hash_id}")
async def get_info(hash_id: str):
    file_data = await file_db.get_file(hash_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")
    
    await file_db.inc_view(hash_id)
    return {
        "name": file_data.get("file_name", "Unknown"),
        "size": file_data.get("file_size", 0),
        "views": file_data.get("views", 0),
        "stream_url": f"/stream/{hash_id}"
    }

@app.get("/stream/{hash_id}")
async def stream_file(hash_id: str):
    file_data = await file_db.get_file(hash_id)
    if not file_data:
        raise HTTPException(status_code=404)

    async def streamer():
        async for chunk in bot_client.stream_media(file_data["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file_data.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT)
