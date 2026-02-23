import asyncio
import uvloop
from config import Config
from pyrogram import Client

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

tg_bot = Client(
    "MainBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="main_bot/plugins")
)
