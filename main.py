import asyncio
import uvicorn
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import Config

# --- 1. INITIALIZE BOT FIRST ---
from bot_client import tg_bot 
# -------------------------------

from bot.server.auth_routes import router as auth_router
from bot.server.stream_routes import router as stream_router
from bot.clone import load_all_clones, db, CLONE_BOTS # Added CLONE_BOTS import

# Import plugins to ensure they load
from bot.plugins import start, commands, files

app = FastAPI()
files_col = db.files # Access DB for cleaner task

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream_router)
app.include_router(auth_router)

# --- UPDATED HEALTH CHECK ---
@app.get("/")
async def health_check():
    return JSONResponse({
        "status": "running",
        "main_bot": "online",
        "active_clones": len(CLONE_BOTS), # Real-time count of connected clones
        "timestamp": time.time()
    })

# --- UPDATED BACKGROUND TASK: CLONE-AWARE CLEANER ---
async def delete_expired_files():
    """
    Finds and deletes files that have passed their expiry time.
    Supports deleting from the correct channel using the correct bot client.
    """
    while True:
        try:
            now = time.time()
            # Find files where expire_at is less than current time
            async for file in files_col.find({"expire_at": {"$lt": now, "$ne": None}}):
                print(f"🗑️ Deleting expired file: {file.get('file_name')}")
                
                try:
                    # Identify the correct client and channel
                    user_id = file.get("user_id")
                    # Use clone client if user has one, else use main bot
                    worker_client = CLONE_BOTS.get(user_id, tg_bot)
                    
                    # Identify correct channel (User's own channel or Global Log)
                    channel_id = file.get("log_channel", Config.LOG_CHANNEL_ID)
                    
                    # 1. Delete from the specific Telegram Log Channel
                    await worker_client.delete_messages(channel_id, file['log_msg_id'])
                except Exception as e:
                    print(f"Telegram Delete Error (File {file.get('file_name')}): {e}")
                
                # 2. Delete from Database regardless of Telegram deletion success
                await files_col.delete_one({"_id": file['_id']})
                
        except Exception as e:
            print(f"Cleaner Task Error: {e}")
        
        await asyncio.sleep(60) # Run check every 60 seconds

async def start_services():
    print("---------------------------------")
    print("   Starting FastAPI + Bot Network")
    print("---------------------------------")

    # 1. Start Main Bot
    await tg_bot.start()
    me = await tg_bot.get_me()
    print(f"✅ Main Bot Started: @{me.username}")

    # 2. Start Clones (Reboot existing bots from DB)
    await load_all_clones()

    # 3. Start Background Tasks
    asyncio.create_task(delete_expired_files())

    # 4. Start Web Server
    print(f"🌍 Server running at {Config.BASE_URL}")
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
    
    # Cleanup on shutdown
    await tg_bot.stop()

if __name__ == "__main__":
    try:
        # Use uvloop for better performance as defined in bot_client.py
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("\n🛑 Services stopped manually.")
