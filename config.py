import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "12345"))
    API_HASH = os.environ.get("API_HASH", "your_hash")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://...")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-100..."))
    DB_NAME = os.environ.get("DB_NAME", "FileBot")