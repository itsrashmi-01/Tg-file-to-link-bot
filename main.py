import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from bot_client import tg_bot
from bot.clone import db, active_clones
from pyrogram import Client
from config import Config

# Fix for cloud logging
sys.stdout.reconfigure(encoding='utf-8')

async def start_clones():
    cursor = db.clones.find({})
    async for clone in cursor:
        try:
            client = Client(f"clone_{clone['user_id']}", 
                            api_id=Config.API_ID, 
                            api_hash=Config.API_HASH, 
                            bot_token=clone['token'])
            await client.start()
            active_clones[clone['user_id']] = client
        except Exception as e:
            print(f"Failed to start clone {clone['user_id']}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Non-blocking Bot Startup
    try:
        await tg_bot.start()
        asyncio.create_task(start_clones())
    except Exception as e:
        app.state.bot_error = str(e)
    
    yield
    await tg_bot.stop()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    error = getattr(app.state, 'bot_error', None)
    return {
        "status": "online" if not error else "degraded",
        "bot_running": tg_bot.is_connected,
        "error": error
    }

# Include routers (auth_routes, stream_routes) here
# app.include_router(...)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
