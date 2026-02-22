import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def _get_int(key, default):
        try:
            return int(os.getenv(key, default))
        except ValueError:
            return default

    API_ID = _get_int("API_ID", 0)
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Database
    MONGO_URL = os.getenv("MONGO_URL") or os.getenv("DB_URL", "")
    DB_NAME = os.getenv("DB_NAME", "Cluster0")
    
    # Channels & Admins
    LOG_CHANNEL_ID = _get_int("LOG_CHANNEL_ID", 0)
    FORCE_SUB_CHANNEL = _get_int("FORCE_SUB_CHANNEL", 0) 
    FORCE_SUB_URL = os.getenv("FORCE_SUB_URL", "")
    
    # Admins List
    ADMIN_IDS = []
    if os.getenv("ADMIN_IDS"):
        try:
            ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS").split()]
        except:
            pass

    # Web
    PORT = _get_int("PORT", 8080)
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
    BLOGGER_URL = os.getenv("BLOGGER_URL", "").rstrip("/")
