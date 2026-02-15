import asyncio
from config import Config

# ==================================================================
# 1. CRITICAL FIX: Ensure Loop Exists Before Pyrogram Loads
# ==================================================================
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
# ==================================================================

from pyrogram import Client

# 2. Initialize the Main Bot
bot = Client(
    "FileStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot")
)
