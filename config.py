import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Your Telegram ID
    
    # --- DATABASES ---
    MONGO_URL = os.getenv("MONGO_URL", "")
    # Separate DB for Clones (Defaults to Main DB if not set)
    CLONE_MONGO_URL = os.getenv("CLONE_MONGO_URL", MONGO_URL) 

    PORT = int(os.getenv("PORT", 10000))
    URL = os.getenv("URL", "https://your-worker.workers.dev")
    BLOGGER_URL = os.getenv("BLOGGER_URL", "") # Optional: Your Blogger URL
    
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "0"))
    FORCE_SUB_LINK = os.getenv("FORCE_SUB_LINK", "")
    BOT_PIC = os.getenv("BOT_PIC", "https://i.imgur.com/8Qj8X9L.jpeg")

    # --- PLAN LIMITS ---
    FREE_DAILY_LIMIT = 5       
    FREE_PASSWORD_LIMIT = 10   
    FREE_EXPIRY_LIMIT = 5
    
    # --- REFERRAL SETTINGS ---
    REFERRAL_POINTS = 10       
    PREMIUM_COST_WEEKLY = 100  
    PREMIUM_COST_MONTHLY = 300