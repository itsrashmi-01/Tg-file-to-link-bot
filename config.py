import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 1. Telegram API Keys
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

    # 2. Database
    MONGO_URL = os.getenv("MONGO_URL", "")
    
    # 3. Channels
    try:
        LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    except:
        LOG_CHANNEL = 0
        
    try:
        FORCE_SUB_CHANNEL = int(os.getenv("FORCE_SUB_CHANNEL", "0"))
    except:
        FORCE_SUB_CHANNEL = 0
        
    FORCE_SUB_LINK = os.getenv("FORCE_SUB_LINK", "")

    # 4. Server Config
    PORT = int(os.getenv("PORT", 8000))
    # Your Render URL (No trailing slash)
    URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")

    # 5. Blogger Link (Optional)
    BLOGGER_URL = os.getenv("BLOGGER_URL", "")

    # 6. Assets
    BOT_PIC = os.getenv("BOT_PIC", "https://i.imgur.com/8Qj8X9L.jpeg")
