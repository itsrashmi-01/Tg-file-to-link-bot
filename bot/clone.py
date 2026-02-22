import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class LazyMotorClient:
    def __init__(self):
        self._client = None
        self._db = None

    @property
    def client(self):
        if self._client is None:
            self._client = AsyncIOMotorClient(Config.MONGO_URL)
        return self._client

    @property
    def db(self):
        if self._db is None:
            self._db = self.client[Config.DB_NAME]
        return self._db

    def __getattr__(self, name):
        return getattr(self.db, name)
    
    def __getitem__(self, name):
        return self.db[name]

# Global DB Instance
db = LazyMotorClient()

# --- CLONE FUNCTIONS ---
CLONE_BOTS = {}

async def start_clone(token, user_id, log_channel):
    try:
        from pyrogram import Client
        session_name = f":memory:{user_id}"
        client = Client(
            session_name,
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            plugins=dict(root="bot/plugins"),
            in_memory=True
        )
        client.log_channel = log_channel 
        client.owner_id = int(user_id)
        await client.start()
        CLONE_BOTS[user_id] = client
        return client, None
    except Exception as e:
        return None, str(e)

async def stop_clone(user_id):
    if user_id in CLONE_BOTS:
        try: await CLONE_BOTS[user_id].stop()
        except: pass
        del CLONE_BOTS[user_id]

async def load_all_clones():
    print("♻️ Loading Clones...")
    count = 0
    # Access db.clones HERE, inside the async function
    async for doc in db.clones.find():
        token = doc.get("token")
        user_id = doc.get("user_id")
        log_channel = doc.get("log_channel")
        if token and user_id:
            client, err = await start_clone(token, user_id, log_channel)
            if client: count += 1
    print(f"✅ Loaded {count} Clones.")
