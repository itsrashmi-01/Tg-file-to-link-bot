import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    
    # Database URIs
    MAIN_MONGO_URI = os.environ.get("MAIN_MONGO_URI", "")
    CLONE_MONGO_URI = os.environ.get("CLONE_MONGO_URI", "")
    
    # Web Server
    BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
    
    # Admins
    SUDO_USERS = [int(x) for x in os.environ.get("SUDO_USERS", "").split()]