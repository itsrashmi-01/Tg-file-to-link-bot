import asyncio
from pyrogram import Client
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient

# Database Setup
mongo_client = AsyncIOMotorClient(Config.MONGO_URL)
db = mongo_client[Config.DB_NAME]
clones_col = db.clones

# Dictionary to keep track of running clones
CLONE_BOTS = {}

async def start_clone(token, user_id, log_channel):
    try:
        # Create unique session name
        session_name = f":memory:"
        
        client = Client(
            session_name,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            plugins=dict(root="bot/plugins"),
            in_memory=True
        )
        
        # --- CRITICAL: Attach the Log Channel ID to the Client ---
        client.log_channel = int(log_channel) 
        client.owner_id = int(user_id)
        # ---------------------------------------------------------

        await client.start()
        me = await client.get_me()
        
        # Save running client to memory
        CLONE_BOTS[user_id] = client
        
        return client
    except Exception as e:
        print(f"Clone Start Error: {e}")
        return None

async def stop_clone(user_id):
    if user_id in CLONE_BOTS:
        await CLONE_BOTS[user_id].stop()
        del CLONE_BOTS[user_id]

async def load_all_clones():
    print("♻️ Loading Clones...")
    count = 0
    async for doc in clones_col.find():
        token = doc.get("token")
        user_id = doc.get("user_id")
        log_channel = doc.get("log_channel") # Load from DB
        
        if token and user_id and log_channel:
            await start_clone(token, user_id, log_channel)
            count += 1
    print(f"✅ Loaded {count} Clones.")
