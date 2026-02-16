from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class MainDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MAIN_MONGO_URI)
        self.db = self.client["bot_manager"]
        self.clones = self.db["clones"]

    async def add_clone(self, token, channel_id, owner_id):
        bot_id = token.split(':')[0]
        await self.clones.update_one(
            {"bot_id": bot_id},
            {"$set": {"token": token, "channel_id": channel_id, "owner_id": owner_id}},
            upsert=True
        )

    async def get_all_clones(self):
        return self.clones.find()

main_db = MainDB()