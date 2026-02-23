import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MONGO_URL = os.getenv("MONGO_URL", "")
    DB_NAME = "Cluster0"
    
    # Main Bot Log Channel
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
    
    # Server Config
    PORT = int(os.getenv("PORT", 8080))
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
    BLOGGER_URL = os.getenv("BLOGGER_URL", "").rstrip("/") # Optional

    # Force Subscribe
    FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "0"))
    FORCE_SUB_URL = os.getenv("FORCE_SUB_URL", "")

    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split()] if os.getenv("ADMIN_IDS") else []
