import asyncio
from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBot
clones_col = db.clones
RUNNING_CLONES = {}

async def start_clone(token, user_id):
    try:
        # Clones use 'memory' session to keep container stateless
        client = Client(
            name=f":memory:{user_id}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            in_memory=True,
            plugins=dict(root="bot/plugins") # Shares plugins with main bot
        )
        await client.start()
        me = await client.get_me()
        
        # Store running instance
        RUNNING_CLONES[me.id] = client
        print(f"   🚀 Clone Started: @{me.username}")
        return me
    except Exception as e:
        print(f"   ❌ Failed to start clone {user_id}: {e}")
        return None

async def load_all_clones():
    print("🤖 Loading Clones...")
    async for doc in clones_col.find():
        await start_clone(doc['token'], doc['user_id'])