import uvicorn
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bot import bot_client  # Ensure this is exported in bot/__init__.py
from web.routes import router as web_router
from config import Config

# --- 1. Setup Web Server ---
app = FastAPI(title="TG Enterprise Bot")

# Allow Blogger (and others) to access your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the routes from web/routes.py
app.include_router(web_router)

@app.get("/")
async def health_check():
    return {"status": "Running", "bot": "Online"}

# --- 2. Lifecycle Management ---
@app.on_event("startup")
async def start_bot():
    print("🤖 Starting Telegram Bot...")
    await bot_client.start()
    print(f"✅ Bot Started as @{bot_client.me.username}")

@app.on_event("shutdown")
async def stop_bot():
    print("😴 Stopping Telegram Bot...")
    await bot_client.stop()

# --- 3. Run Server ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT, reload=False)
