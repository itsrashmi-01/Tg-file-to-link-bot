from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import secrets

class FileDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client["prod_db"]
        self.col = self.db["files"]

    async def add_file(self, data):
        data["_id"] = secrets.token_urlsafe(8)
        await self.col.insert_one(data)
        return data["_id"]

    async def get_file(self, slug):
        return await self.col.find_one({"_id": slug})

file_db = FileDB()
