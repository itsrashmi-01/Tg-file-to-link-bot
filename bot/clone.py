import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class LazyMotorClient:
    def __init__(self, url, db_name):
        self.url = url
        self.db_name = db_name
        self._client = None
        self._db = None

    @property
    def client(self):
        if self._client is None:
            if not self.url: return None
            self._client = AsyncIOMotorClient(self.url)
        return self._client

    @property
    def db(self):
        if self._db is None and self.client:
            self._db = self.client[self.db_name]
        return self._db

    def __getattr__(self, name):
        if self.db is None: return None
        return getattr(self.db, name)
    
    def __getitem__(self, name):
        if self.db is None: return None
        return self.db[name]

# --- DATABASES ---
# Main Bot DB
db = LazyMotorClient(Config.MONGO_URL, Config.DB_NAME)

# Clone Bots DB
cdb = LazyMotorClient(Config.CLONE_MONGO_URL, Config.CLONE_DB_NAME)

# --- DB SELECTOR HELPER ---
def get_db(client):
    """Returns 'db' for Main Bot and 'cdb' for Clone Bots"""
    # Main Bot ID extraction
    try:
        main_bot_id = int(Config.BOT_TOKEN.split(":")[0])
        if client.me.id == main_bot_id:
            return db
    except:
        pass
    # Default to Clone DB for others
    return cdb

# --- CLONE LOGIC ---
CLONE_BOTS = {}

async def start_clone(token, user_id, log_channel):
    try:
        from pyrogram import Client
        session = f":memory:{user_id}"
        app = Client(session, api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=token, in_memory=True)
        app.log_channel = log_channel
        app.owner_id = int(user_id)
        await app.start()
        CLONE_BOTS[user_id] = app
        return app, None
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
    # We load list of clones from MAIN DB
    try:
        async for doc in db.clones.find():
            if doc.get("token"):
                await start_clone(doc["token"], doc.get("user_id"), doc.get("log_channel"))
                count += 1
    except Exception as e:
        print(f"⚠️ Clone Load Error: {e}")
    print(f"✅ Loaded {count} Clones.")
