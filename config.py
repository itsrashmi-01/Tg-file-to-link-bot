import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def _get_int(key, default):
        try: return int(os.getenv(key, default))
        except: return default

    API_ID = _get_int("API_ID", 0)
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # --- Database 1: Main Bot ---
    MONGO_URL = os.getenv("MONGO_URL") or os.getenv("DB_URL", "")
    DB_NAME = os.getenv("DB_NAME", "Cluster0")
    
    # --- Database 2: Clone Bots ---
    # If CLONE_MONGO_URL is not set, it defaults to the same cluster as Main but different DB Name
    CLONE_MONGO_URL = os.getenv("CLONE_MONGO_URL") or MONGO_URL
    CLONE_DB_NAME = os.getenv("CLONE_DB_NAME", "CloneCluster")
    
    # Channels
    LOG_CHANNEL_ID = _get_int("LOG_CHANNEL_ID", 0)
    
    # Admins
    ADMIN_IDS = []
    raw_admins = os.getenv("ADMIN_IDS", "")
    if raw_admins:
        try: ADMIN_IDS = [int(x) for x in raw_admins.split()]
        except: pass

    # Web
    PORT = _get_int("PORT", 8080)
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
    BLOGGER_URL = os.getenv("BLOGGER_URL", "").rstrip("/")
