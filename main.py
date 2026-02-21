import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import Config

# --- FIX: IMPORT THIS FIRST ---
# This ensures the event loop is created BEFORE auth_routes imports Pyrogram
from bot_client import bot 
# ------------------------------

from bot.server.auth_routes import router as auth_router
from bot.server.stream_routes import router as stream_router
from bot.clone import load_all_clones

app = FastAPI()

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

async def start_services():
    print("---------------------------------")
    print("   Starting FastAPI + Bot        ")
    print("---------------------------------")

    # 1. Start Main Bot
    await bot.start()
    me = await bot.get_me()
    print(f"✅ Main Bot Started: @{me.username}")

    # 2. Start Clones
    await load_all_clones()

    # 3. Start Web Server
    print(f"🌍 Server running at {Config.BASE_URL}")
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT)
    server = uvicorn.Server(config)
    await server.serve()
    
    # 4. Cleanup
    await bot.stop()

if __name__ == "__main__":
    try:
        # Get the loop that was created in bot_client.py
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
