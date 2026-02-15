import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import Config
from bot_client import bot
from server.stream_routes import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

async def start_services():
    print("🚀 Starting Bot...")
    await bot.start()
    
    print(f"🌍 Starting Web Server on port {Config.PORT}...")
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT)
    server = uvicorn.Server(config)
    await server.serve()
    
    print("🛑 Stopping Bot...")
    await bot.stop()

if __name__ == "__main__":
    # The loop was already created in bot_client.py, so we just get it
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
