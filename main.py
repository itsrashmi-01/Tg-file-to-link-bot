import asyncio
from pyrogram import Client
from fastapi import FastAPI
import uvicorn
from config import Config

# 1. FastAPI App for Render's Health Check
app = FastAPI()

@app.get("/")
async def health_check():
    return {"status": "running", "bot": "active"}

# 2. Pyrogram Bot Client
class Bot(Client):
    def __init__(self):
        super().__init__(
            "file_converter",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="bot/plugins")
        )

    async def start(self):
        await super().start()
        print("Bot Started!")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped!")

# 3. Runner Logic
async def main():
    bot = Bot()
    # Run the bot in the background
    await bot.start()
    
    # Run the Web Server (FastAPI) on the port Render provides
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)
    
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())