import asyncio
from pyrogram import Client
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(Config.MONGO_URL)
db = mongo_client[Config.DB_NAME]
clones_col = db.clones
CLONE_BOTS = {}

async def start_clone(token, user_id, log_channel=None):
    try:
        client = Client(
            f"clone_{user_id}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            plugins=dict(root="clone_bot/plugins"),
            in_memory=True
        )
        client.log_channel = int(log_channel) if log_channel else None
        client.owner_id = int(user_id)
        await client.start()
        CLONE_BOTS[user_id] = client
        return client
    except Exception as e:
        print(f"Clone Error: {e}")
        return None

async def stop_clone(user_id):
    if user_id in CLONE_BOTS:
        await CLONE_BOTS[user_id].stop()
        del CLONE_BOTS[user_id]

async def load_all_clones():
    async for doc in clones_col.find():
        await start_clone(doc["token"], doc["user_id"], doc.get("log_channel"))
