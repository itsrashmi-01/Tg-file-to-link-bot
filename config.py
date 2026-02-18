import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 1. Telegram API Keys
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # 2. Database (We map DB_URL to MONGO_URL for backward compatibility)
    MONGO_URL = os.getenv("MONGO_URL", "")
    DB_URL = MONGO_URL  # <--- FIX: Alias DB_URL to MONGO_URL
    DB_NAME = "Cluster0"

    # 3. Channels
    # Convert to int to prevent "PeerIdInvalid" errors
    try:
        LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
    except ValueError:
        LOG_CHANNEL_ID = 0

    # 4. Server Config
    PORT = int(os.getenv("PORT", 8080))
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
