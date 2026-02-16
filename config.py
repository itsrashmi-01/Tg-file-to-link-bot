import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URI = os.environ.get("MONGO_URI", "")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL_ID", 0))
    # Your Blogger Page URL (e.g., https://mybot.blogspot.com/p/download.html)
    BLOG_URL = os.environ.get("BLOG_URL", "") 
    # Force Sub Channel ID (Start with -100)
    FSUB_ID = int(os.environ.get("FSUB_ID", 0))
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split()]
    PORT = int(os.environ.get("PORT", 8080))