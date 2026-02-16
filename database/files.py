from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import secrets

class FileDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client["tg_bot_pro"]
        self.col = self.db["files"]

    async def add_file(self, file_info):
        # Generate a short, url-safe hash (better than Mongo ID)
        url_hash = secrets.token_urlsafe(8)
        file_info["_id"] = url_hash
        file_info["views"] = 0
        await self.col.insert_one(file_info)
        return url_hash

    async def get_file(self, url_hash):
        return await self.col.find_one({"_id": url_hash})

    async def inc_view(self, url_hash):
        await self.col.update_one({"_id": url_hash}, {"$inc": {"views": 1}})

file_db = FileDB()