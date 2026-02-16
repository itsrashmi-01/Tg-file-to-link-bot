from pyrogram import Client
from config import Config

# Initialize the client instance
bot_client = Client(
    "enterprise_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)
