import asyncio
import uvloop
from config import Config

# --- CRITICAL FIX START ---
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# --- CRITICAL FIX END ---

from pyrogram import Client

# Initialize the Main Bot
# RENAMED TO 'tg_bot' TO AVOID CONFLICT WITH 'bot' FOLDER
tg_bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
