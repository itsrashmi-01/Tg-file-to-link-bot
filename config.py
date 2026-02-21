import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ... (Keep existing configurations) ...
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MONGO_URL = os.getenv("MONGO_URL", "")
    DB_URL = MONGO_URL
    DB_NAME = "Cluster0"
    try:
        LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
    except ValueError:
        LOG_CHANNEL_ID = 0
    PORT = int(os.getenv("PORT", 8080))
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
    BLOGGER_URL = os.getenv("BLOGGER_URL", "").rstrip("/")

    # --- NEW CONFIGS ---
    # Force Subscribe Channel ID (Start with -100...)
    FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "0")) 
    # Link to the channel (e.g., https://t.me/mychannel)
    FORCE_SUB_URL = os.getenv("FORCE_SUB_URL", "")
    # List of Admin User IDs (separated by spaces in .env)
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split()] if os.getenv("ADMIN_IDS") else []
