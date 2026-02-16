import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    
    MONGO_URL = os.getenv("MONGO_URL", "")
    CLONE_MONGO_URL = os.getenv("CLONE_MONGO_URL", MONGO_URL) 

    # REPLACE THIS WITH YOUR RENDER URL
    URL = os.getenv("URL", "https://your-app.onrender.com") 
    
    PORT = int(os.getenv("PORT", 10000))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "0"))
    FORCE_SUB_LINK = os.getenv("FORCE_SUB_LINK", "")
    
    FREE_DAILY_LIMIT = 5
    FREE_EXPIRY_LIMIT = 5
    FREE_PASSWORD_LIMIT = 10
    REFERRAL_POINTS = 10
    PREMIUM_COST_WEEKLY = 100
    PREMIUM_COST_MONTHLY = 300
    BOT_PIC = "https://i.imgur.com/8Qj8X9L.jpeg"
