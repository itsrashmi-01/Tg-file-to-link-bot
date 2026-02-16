import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from pyrogram import Client # Fixes "Client not defined" error

# Local Imports
from config import Config
from bot import bot_client
from database.files import file_db

# --- 1. Lifespan (Fixes "Attached to different loop" error) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    try:
        # This starts the bot within the FastAPI event loop
        await bot_client.start()
        print(f"✅ Bot Started: @{bot_client.me.username}")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
    
    yield  # Application runs here
    
    print("😴 Stopping Telegram Bot...")
    await bot_client.stop()

# --- 2. FastAPI Setup ---
app = FastAPI(title="Enterprise TG Bot", lifespan=lifespan)

# Allow Blogger to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Web Routes ---

@app.get("/")
async def health():
    return {"status": "running", "message": "Bot is active"}

@app.get("/api/info/{hash_id}")
async def get_info(hash_id: str):
    """Blogger calls this to get file name and size"""
    # Uses the fixed string-based search
    file_data = await file_db.get_file(hash_id)
    
    if not file_data:
        print(f"🔍 404 Error: Hash {hash_id} not found in DB")
        raise HTTPException(status_code=404, detail="File not found")
    
    # Increment views
    await file_db.inc_view(hash_id)
    
    return {
        "name": file_data.get("file_name", "Unknown File"),
        "size": file_data.get("file_size", 0),
        "views": file_data.get("views", 0),
        "stream_url": f"/stream/{hash_id}"
    }

@app.get("/stream/{hash_id}")
async def stream_file(hash_id: str):
    """Directly streams the file from Telegram to the browser"""
    file_data = await file_db.get_file(hash_id)
    if not file_data:
        raise HTTPException(status_code=404)

    async def streamer():
        # This acts as a proxy: Telegram -> Render -> User
        async for chunk in bot_client.stream_media(file_data["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file_data.get("mime_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
            "Content-Length": str(file_data.get("file_size", ""))
        }
    )

# --- 4. Entry Point ---
if __name__ == "__main__":
    # Standard Render port is 8000 or $PORT
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT)
