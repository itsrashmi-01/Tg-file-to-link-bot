from pyrogram import Client
from config import Config

# Initialize the Main Bot
# We do NOT set the event loop policy here because Uvicorn handles it.
tg_bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
