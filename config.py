import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Database
    DB_URL = os.environ.get("DB_URL", "")
    DB_NAME = os.environ.get("DB_NAME", "Cluster0")
    
    # Web / Server
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")
    PORT = int(os.environ.get("PORT", 8080))
    
    # Channel to store files for direct links
    LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", 0))