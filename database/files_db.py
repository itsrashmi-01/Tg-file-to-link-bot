from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import secrets

class FilesDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.CLONE_MONGO_URI)
        self.db = self.client["file_storage"]
        self.files = self.db["files"]

    async def save_file(self, bot_id, file_id, file_name, mime_type):
        file_hash = secrets.token_urlsafe(8)
        await self.files.insert_one({
            "bot_id": bot_id,
            "file_hash": file_hash,
            "file_id": file_id,
            "file_name": file_name,
            "mime_type": mime_type
        })
        return file_hash

    async def get_file(self, bot_id, file_hash):
        return await self.files.find_one({"bot_id": bot_id, "file_hash": file_hash})

files_db = FilesDB()