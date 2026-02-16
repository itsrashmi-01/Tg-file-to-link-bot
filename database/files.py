from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import secrets

class FileDB:
    def __init__(self):
        # The client is initialized using the MONGO_URI from your Config
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client["tg_bot_pro"]
        self.col = self.db["files"]

    async def add_file(self, file_info: dict):
        """
        Generates a unique 8-character string ID and stores file metadata.
        """
        # Generate a short, URL-safe string (e.g., 'cU8tYg8kH_Y')
        url_hash = secrets.token_urlsafe(8)
        
        # We set the custom string as the MongoDB _id
        file_info["_id"] = url_hash
        file_info["views"] = 0
        
        await self.col.insert_one(file_info)
        return url_hash

    async def get_file(self, url_hash: str):
        """
        Retrieves file data using the custom string ID.
        Note: We do NOT use ObjectId() here because our _id is a String.
        """
        try:
            return await self.col.find_one({"_id": url_hash})
        except Exception as e:
            print(f"❌ Database Query Error: {e}")
            return None

    async def inc_view(self, url_hash: str):
        """
        Increments the view counter for a specific file.
        """
        try:
            await self.col.update_one(
                {"_id": url_hash}, 
                {"$inc": {"views": 1}}
            )
        except Exception as e:
            print(f"❌ Database Update Error: {e}")

# Create a singleton instance to be used across the app
file_db = FileDB()
