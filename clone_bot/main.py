from pyrogram import Client
from config import Config
from bot import db

class CloneManager:
    def __init__(self):
        self.clones = []
        self.collection = db['clones']

    async def start_clones(self):
        print("🔄 Loading Clones...")
        async for clone in self.collection.find():
            try:
                token = clone.get('token')
                if not token: continue
                
                # IMPORTANT: Pointing to 'clone_bot/plugins'
                client = Client(
                    name=f"clone_{clone['user_id']}",
                    api_id=Config.API_ID,
                    api_hash=Config.API_HASH,
                    bot_token=token,
                    plugins=dict(root="clone_bot/plugins") 
                )
                
                await client.start()
                self.clones.append(client)
                me = await client.get_me()
                print(f"   ✅ Clone Started: @{me.username}")
                
            except Exception as e:
                print(f"   ❌ Clone Error ({clone.get('user_id')}): {e}")

    async def stop_clones(self):
        for clone in self.clones:
            try:
                await clone.stop()
            except:
                pass