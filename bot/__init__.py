# bot/__init__.py
from pyrogram import Client
from config import Config

# Initialize the Client
bot_client = Client(
    "enterprise_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins") # This loads your plugins automatically
)
