import os
import sys

# --- FORCE UNBUFFERED OUTPUT (So you see logs immediately) ---
sys.stdout.reconfigure(encoding='utf-8')

print("⏳ Initializing Application...")

try:
    import asyncio
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    
    print("✅ Libraries Imported.")

    # Check Config Imports
    try:
        from config import Config
        print("✅ Config Loaded.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Config Import Failed. Check Env Vars.\nError: {e}")
        sys.exit(1)

    # Check Bot Imports
    try:
        from bot_client import tg_bot
        from bot.server import auth_routes
        from bot.clone import load_all_clones
        print("✅ Bot Modules Loaded.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Bot Module Import Failed.\nError: {e}")
        sys.exit(1)

    # --- BACKGROUND TASK ---
    async def start_bot_services():
        """Starts the bot in background without blocking Web Server"""
        try:
            print("🚀 Starting Telegram Bot...")
            await tg_bot.start()
            me = await tg_bot.get_me()
            print(f"✅ Main Bot Started: @{me.username}")
            
            print("♻️ Loading Clone Bots...")
            await load_all_clones()
            print("✅ Clones Ready.")
        except Exception as e:
            print(f"⚠️ BOT STARTUP FAILED (Web Server still running): {e}")

    # --- LIFESPAN MANAGER ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start Bot in Background
        asyncio.create_task(start_bot_services())
        yield
        # Stop Bot
        try:
            print("🛑 Stopping Bot...")
            await tg_bot.stop()
        except:
            pass

    # --- FASTAPI APP ---
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)

    @app.get("/")
    async def health_check():
        return {"status": "active", "service": "Cloud Manager Bot"}

except Exception as e:
    print(f"❌ GLOBAL CRASH: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f"🌍 Starting Web Server on 0.0.0.0:{port}...")
        
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=port, 
            log_level="info"
        )
    except Exception as e:
        print(f"❌ SERVER START ERROR: {e}")
