from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import secrets
import time

class FilesDB:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.CLONE_MONGO_URI)
        self.db = self.client["file_storage"]
        self.files = self.db["files"]

    async def save_file(self, bot_id, media, caption=""):
        # We generate a short, unique URL-safe hash (e.g., "AbCd123")
        file_hash = secrets.token_urlsafe(8)
        
        # We save the crucial details to MongoDB
        file_data = {
            "bot_id": bot_id,
            "file_hash": file_hash,
            "file_id": media.file_id,               # The key to accessing the file on Telegram
            "file_unique_id": media.file_unique_id, # Persistent ID for matching
            "file_name": getattr(media, "file_name", "Unknown File"),
            "mime_type": getattr(media, "mime_type", "application/octet-stream"),
            "file_size": getattr(media, "file_size", 0),
            "caption": caption,
            "created_at": time.time()
        }
        
        await self.files.insert_one(file_data)
        return file_hash

    async def get_file(self, bot_id, file_hash):
        return await self.files.find_one({"bot_id": bot_id, "file_hash": file_hash})

files_db = FilesDB()
