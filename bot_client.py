import asyncio
import uvloop
from config import Config

# --- CRITICAL FIX: Setup loop BEFORE importing pyrogram ---
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client

# Initialize the Main Bot
tg_bot = Client(
    "MainBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="main_bot/plugins")
)
