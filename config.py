import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MONGO_URL = os.getenv("MONGO_URL", "")
    CLONE_MONGO_URL = os.getenv("CLONE_MONGO_URL", "")
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    DOMAIN = os.getenv("DOMAIN", "http://localhost:8000")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
