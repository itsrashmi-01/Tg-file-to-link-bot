import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class LazyMotorClient:
    """
    A wrapper that delays the Motor Client initialization 
    until the Event Loop is actually running.
    """
    def __init__(self):
        self._client = None
        self._db = None

    @property
    def client(self):
        if self._client is None:
            # This runs only when we first try to use the DB
            # By this time, Uvicorn has started the loop.
            self._client = AsyncIOMotorClient(Config.MONGO_URL)
        return self._client

    @property
    def db(self):
        if self._db is None:
            self._db = self.client[Config.DB_NAME]
        return self._db

    # --- Proxy methods to behave like a Database object ---
    def __getattr__(self, name):
        # Allow accessing collections directly: db.users
        return getattr(self.db, name)
    
    def __getitem__(self, name):
        # Allow accessing collections via dict: db['users']
        return self.db[name]

# Create the Global DB Instance
# This does NOT connect yet. It just creates the wrapper.
db = LazyMotorClient()

# Define Collections (These are now proxies)
clones_col = db.clones

# --- CLONE FUNCTIONS ---
# We keep these as they were, but they use the global `db` which auto-connects
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
    # db.clones access triggers the connection here
    async for doc in db.clones.find():
        token = doc.get("token")
        user_id = doc.get("user_id")
        log_channel = doc.get("log_channel")
        if token and user_id:
            client, err = await start_clone(token, user_id, log_channel)
            if client: count += 1
    print(f"✅ Loaded {count} Clones.")
