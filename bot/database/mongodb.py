from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self):
        self._client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self._client[Config.DB_NAME]
        self.col = self.db.files

    async def save_file(self, file_id, msg_id):
        # We use msg_id as the unique key for the link
        await self.col.insert_one({"_id": str(msg_id), "file_id": file_id})
        return str(msg_id)

    async def get_file(self, file_id):
        return await self.col.find_one({"_id": file_id})

db = Database()