from pyrogram import Client
from config import Config

bot_client = Client(
    "bot_instance",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
