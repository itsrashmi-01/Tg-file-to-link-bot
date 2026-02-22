import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class LazyMotorClient:
    def __init__(self, uri, name):
        self._uri = uri
        self._name = name
        self._client = None
        self._db = None

    def _get_db(self):
        if self._client is None:
            self._client = AsyncIOMotorClient(self._uri)
            self._db = self._client[self._name]
        return self._db

    def __getattr__(self, name):
        # Proxies collection access: db.users -> db._get_db().users
        return getattr(self._get_db(), name)

# Global Proxy Objects
db = LazyMotorClient(Config.MONGO_URL, "main_bot")
cdb = LazyMotorClient(Config.CLONE_MONGO_URL, "clone_bots")

async def get_db_for_bot(is_clone=False):
    return cdb if is_clone else db

# Store active pyrogram clients for clones
active_clones = {}
