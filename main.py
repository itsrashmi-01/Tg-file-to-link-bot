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
from bot.clone import load_all_clones, db

# Import plugins to ensure they load
from bot.plugins import start, commands, files, clone_chat, connect, protect

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

@app.get("/")
async def health_check():
    return JSONResponse({"status": "running", "bot": "online"})

# --- BACKGROUND TASK: DELETE EXPIRED FILES ---
async def delete_expired_files():
    while True:
        try:
            now = time.time()
            # Find files where expire_at exists AND is less than current time
            async for file in files_col.find({"expire_at": {"$lt": now, "$ne": None}}):
                print(f"🗑️ Deleting expired file: {file.get('file_name')}")
                try:
                    # 1. Delete from Telegram Log Channel
                    await tg_bot.delete_messages(Config.LOG_CHANNEL_ID, file['log_msg_id'])
                except Exception as e:
                    print(f"Telegram Delete Error: {e}")
                
                # 2. Delete from Database
                await files_col.delete_one({"_id": file['_id']})
                
        except Exception as e:
            print(f"Cleaner Task Error: {e}")
        
        await asyncio.sleep(60) # Run check every 60 seconds

async def start_services():
    print("---------------------------------")
    print("   Starting FastAPI + Bot        ")
    print("---------------------------------")

    # 1. Start Main Bot
    await tg_bot.start()
    me = await tg_bot.get_me()
    print(f"✅ Main Bot Started: @{me.username}")

    # 2. Start Clones
    await load_all_clones()

    # 3. Start Background Tasks
    asyncio.create_task(delete_expired_files()) # <--- START CLEANER

    # 4. Start Web Server
    print(f"🌍 Server running at {Config.BASE_URL}")
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT)
    server = uvicorn.Server(config)
    await server.serve()
    
    await tg_bot.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass

