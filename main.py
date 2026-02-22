import uvicorn
import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import Config
from bot_client import tg_bot
from bot.server import auth_routes
from bot.clone import load_all_clones

# --- BACKGROUND TASK WRAPPER ---
async def start_bot_services():
    """Starts the bot and loads clones without blocking the Web Server."""
    try:
        print("🚀 Starting Telegram Bot...")
        await tg_bot.start()
        me = await tg_bot.get_me()
        print(f"✅ Main Bot Started: @{me.username}")
        
        print("♻️ Loading Clone Bots...")
        await load_all_clones()
        print("✅ All Clones Loaded.")
    except Exception as e:
        print(f"❌ Bot Startup Error: {e}")

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run bot startup as a background task so it doesn't block the Port binding
    asyncio.create_task(start_bot_services())
    
    yield # The Web Server starts listening HERE
    
    # Shutdown logic
    print("🛑 Stopping Bot...")
    try:
        await tg_bot.stop()
    except:
        pass

# --- FASTAPI APP ---
app = FastAPI(lifespan=lifespan)

# CORS (Allow Web App Access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
app.include_router(auth_routes.router)

@app.get("/")
async def health_check():
    return {"status": "active", "service": "Cloud Manager Bot"}

if __name__ == "__main__":
    # --- CRITICAL FOR RENDER DEPLOYMENT ---
    # 1. Listen on 0.0.0.0 (External Access)
    # 2. Use the PORT environment variable provided by Render
    port = int(os.environ.get("PORT", 8080))
    
    print(f"🌍 Starting Web Server on Port {port}...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        log_level="info"
    )
