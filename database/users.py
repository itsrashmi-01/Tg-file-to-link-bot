from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import time

class UserDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client["tg_bot_pro"]
        self.col = self.db["users"]

    async def add_user(self, user_id, name):
        if not await self.col.find_one({"_id": user_id}):
            await self.col.insert_one({
                "_id": user_id,
                "name": name,
                "join_date": time.time(),
                "is_premium": False,
                "banned": False
            })

    async def get_stats(self):
        return await self.col.count_documents({})

    async def get_all_users(self):
        return self.col.find({})

user_db = UserDB()