from pyrogram import Client
from config import Config

# Main Bot Client (Initialized but not started)
tg_bot = Client(
    "main_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
