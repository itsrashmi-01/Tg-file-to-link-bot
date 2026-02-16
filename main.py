import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

# --- CRITICAL: MUST IMPORT CLIENT DIRECTLY HERE ---
from pyrogram import Client 
from config import Config
from database.files import file_db

# We import the instance, but we need the Class 'Client' for lifespan to work
from bot import bot_client 

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    try:
        # Check if bot_client exists and is an instance of Client
        if bot_client:
            await bot_client.start()
            print(f"✅ Bot Started: @{bot_client.me.username}")
        else:
            print("❌ bot_client instance not found!")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
    
    yield  # Application logic runs here
    
    print("😴 Shutting down...")
    if bot_client and bot_client.is_connected:
        await bot_client.stop()

# --- FastAPI App Setup ---
app = FastAPI(title="Ultimate TG Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/")
async def health():
    return {"status": "alive", "msg": "API is working"}

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
        # Using the bot_client instance to stream
        async for chunk in bot_client.stream_media(file_data["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file_data.get("mime_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'
        }
    )

if __name__ == "__main__":
    # Ensure port is handled correctly for Render
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT)
