import asyncio
import uvloop
from pyrogram import Client
from config import Config

# 1. Set Event Loop Policy (Fixes Render Issues)
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# 2. Initialize Bot
bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)