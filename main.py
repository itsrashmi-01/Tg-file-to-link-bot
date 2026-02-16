import uvicorn
import asyncio
from fastapi import FastAPI
from pyrogram import Client, idle
from config import Config
from bot import bot_client  # Ensure this import works!

app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "Running"}

async def start_services():
    print("🤖 Starting Bot...")
    await bot_client.start()
    print("✅ Bot Started!")
    
    # Keep the bot running in the background
    await idle()

if __name__ == "__main__":
    # We use a trick to run both FastAPI and Pyrogram
    loop = asyncio.get_event_loop()
    
    # 1. Start Web Server in a separate task
    config = uvicorn.Config(app=app, host="0.0.0.0", port=Config.PORT)
    server = uvicorn.Server(config)
    loop.create_task(server.serve())
    
    # 2. Start Bot and Block
    loop.run_until_complete(start_services())
