import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager

# Import your existing modules
from config import Config
from bot import bot_client
from database.files import file_db
from database.users import user_db

# --- 1. Lifespan Management (Fixes the Loop Error) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting Telegram Bot...")
    try:
        await bot_client.start()
        print(f"✅ Bot Started as @{bot_client.me.username}")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        
    yield  # The app stays here while running
    
    print("😴 Stopping Telegram Bot...")
    await bot_client.stop()

# --- 2. FastAPI Setup ---
app = FastAPI(title="Enterprise File Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Web Routes ---

@app.get("/")
async def health_check():
    return {"status": "Running", "bot": "Online"}

@app.get("/api/info/{hash_id}")
async def get_info(hash_id: str):
    """Blogger calls this to get file details"""
    # Fix: Search by string ID, not ObjectId
    file = await file_db.get_file(hash_id)
    
    if not file:
        print(f"🔍 404: Hash {hash_id} not found in DB.")
        raise HTTPException(status_code=404, detail="File not found")
    
    # Optional: track views
    await file_db.inc_view(hash_id)
    
    return {
        "name": file["file_name"],
        "size": file["file_size"],
        "views": file.get("views", 0),
        "stream_url": f"/stream/{hash_id}" 
    }

@app.get("/stream/{hash_id}")
async def stream_file(hash_id: str):
    """Handles the actual file streaming from Telegram"""
    file = await file_db.get_file(hash_id)
    if not file:
        raise HTTPException(status_code=404)

    async def streamer():
        # Streams directly from Telegram to the User
        async for chunk in bot_client.stream_media(file["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{file["file_name"]}"'}
    )

# --- 4. Deployment Entry Point ---
if __name__ == "__main__":
    # Use the "app" string to let Uvicorn handle the loop correctly
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=False)
