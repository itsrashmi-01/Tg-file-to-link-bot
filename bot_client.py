import asyncio
import uvloop
from config import Config

# --- CRITICAL FIX START ---
# We must set the policy and create a loop BEFORE importing Pyrogram.
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# --- CRITICAL FIX END ---

from pyrogram import Client

# Initialize the Main Bot
bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
