import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

# --- CRITICAL: MANDATORY IMPORT AT THE ABSOLUTE TOP ---
from pyrogram import Client 

# Local Imports
from config import Config
from bot import bot_client
from database.files import file_db

# --- 1. Lifespan Management (Fixes the Event Loop Error) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    try:
        # We use the instance imported from 'bot'
        await bot_client.start()
        print(f"✅ Bot Started Successfully: @{bot_client.me.username}")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
    
    yield  # The Web Server is now active
    
    print("😴 Shutting down services...")
    try:
        if bot_client and bot_client.is_connected:
            await bot_client.stop()
    except:
        pass

# --- 2. FastAPI App Setup ---
app = FastAPI(title="Pro File Link Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. API Routes ---

@app.get("/")
async def health():
    # Helper to check if bot is actually connected from your browser
    is_ready = bot_client.is_connected if bot_client else False
    return {"status": "online", "bot_connected": is_ready}

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
