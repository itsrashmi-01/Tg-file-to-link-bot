from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

# Initialize MongoDB
db_client = AsyncIOMotorClient(Config.DB_URL)
db = db_client[Config.DB_NAME]

# Initialize Main Bot
Bot = Client(
    "DirectLinkBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)