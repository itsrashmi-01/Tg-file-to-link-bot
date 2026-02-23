import asyncio
import uvloop
from config import Config

# --- PERFORMANCE FIX ---
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# -----------------------

from pyrogram import Client

# Initialize the Main Bot
tg_bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)

# --- CRITICAL FIX: Attach Attributes to Main Bot ---
# This makes the Main Bot behave consistently with Clones
tg_bot.log_channel = Config.LOG_CHANNEL_ID
tg_bot.owner_id = None # Main Bot has no owner
# ---------------------------------------------------
