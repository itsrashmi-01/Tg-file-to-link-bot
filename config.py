import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URI = os.environ.get("MONGO_URI", "")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
    BLOG_URL = os.environ.get("BLOG_URL", "https://tg-file-to-link.blogspot.com/2026/02/download.html") # Blogger page URL
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split()]
    PORT = int(os.environ.get("PORT", 8000))
