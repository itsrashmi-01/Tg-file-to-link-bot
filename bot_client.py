from pyrogram import Client
from config import Config

# Initialize the Main Bot
# We let Uvicorn manage the event loop. We do NOT set it here.
tg_bot = Client(
    "FastStreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
