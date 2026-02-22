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
        # Use a unique session name for each user to avoid conflicts
        session_name = f":memory:{user_id}"
        
        client = Client(
            session_name,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            plugins=dict(root="bot/plugins"),
            in_memory=True
        )
        
        # --- Fix: Handle Channel ID (Int) vs Username (Str) ---
        # We attach it now; validation happens in commands.py
        client.log_channel = log_channel 
        client.owner_id = int(user_id)
        # ------------------------------------------------------

        await client.start()
        
        # Save running client to memory
        CLONE_BOTS[user_id] = client
        
        return client, None  # Success: Return (Client, No Error)
        
    except Exception as e:
        error_msg = str(e)
        print(f"Clone Start Error: {e}")
        return None, error_msg  # Failure: Return (None, Error Message)

async def stop_clone(user_id):
    if user_id in CLONE_BOTS:
        try:
            await CLONE_BOTS[user_id].stop()
        except:
            pass
        del CLONE_BOTS[user_id]

async def load_all_clones():
    print("♻️ Loading Clones...")
    count = 0
    async for doc in clones_col.find():
        token = doc.get("token")
        user_id = doc.get("user_id")
        log_channel = doc.get("log_channel")
        
        if token and user_id and log_channel:
            client, err = await start_clone(token, user_id, log_channel)
            if client:
                count += 1
            else:
                # If a clone fails to load (e.g. token revoked), remove it
                print(f"❌ Failed to load clone for {user_id}: {err}")
                await clones_col.delete_one({"_id": doc["_id"]})
                
    print(f"✅ Loaded {count} Clones.")
