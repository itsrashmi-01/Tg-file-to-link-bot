
import asyncio
from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

# Main DB Connection
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
clones_col = db.clones

# Dictionary to store active clone clients
RUNNING_CLONES = {} 

async def start_clone_bot(token, log_channel):
    try:
        client = Client(
            name=f"clone_{token.split(':')[0]}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            in_memory=True
        )
        await client.start()
        
        # Verify Log Channel access
        try:
            chat = await client.get_chat(log_channel)
            channel_id = chat.id
        except Exception:
            await client.stop()
            return None, None

        bot_info = await client.get_me()
        
        # Store active client in memory
        RUNNING_CLONES[bot_info.id] = {
            "client": client,
            "log_channel": channel_id
        }
        
        return bot_info, channel_id
    except Exception as e:
        print(f"Clone Start Error: {e}")
        return None, None

async def load_all_clones():
    print("🤖 Loading Clones...")
    count = 0
    async for clone in clones_col.find():
        token = clone['token']
        log_channel = clone['log_channel']
        bot_info, final_id = await start_clone_bot(token, log_channel)
        if bot_info:
            count += 1
    print(f"✅ Loaded {count} Clone Bots.")