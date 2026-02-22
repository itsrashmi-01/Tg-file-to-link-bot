import os
import sys

# Unbuffered Output
sys.stdout.reconfigure(encoding='utf-8')

print("⏳ [Main] Starting Application...")

try:
    import asyncio
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    
    print("✅ [Main] Core Libraries Imported.")

    # Check Config
    try:
        from config import Config
        print("✅ [Main] Config Loaded.")
    except Exception as e:
        print(f"❌ [Main] Config Import Failed: {e}")
        sys.exit(1)

    # Check Bot Client
    try:
        from bot_client import tg_bot
        print("✅ [Main] Bot Client Loaded.")
    except Exception as e:
        print(f"❌ [Main] Bot Client Import Failed: {e}")
        sys.exit(1)

    # Check Routes
    try:
        from bot.server import auth_routes, stream_routes
        from bot.clone import load_all_clones
        print("✅ [Main] Routes Loaded.")
    except Exception as e:
        print(f"❌ [Main] Routes Import Failed (Check bot/utils.py): {e}")
        sys.exit(1)

    # --- BACKGROUND TASK ---
    async def start_bot_services():
        try:
            print("🚀 [Bot] Starting Telegram Bot...")
            await tg_bot.start()
            me = await tg_bot.get_me()
            print(f"✅ [Bot] Started as @{me.username}")
            
            print("♻️ [Bot] Loading Clones...")
            await load_all_clones()
            print("✅ [Bot] Clones Ready.")
        except Exception as e:
            print(f"⚠️ [Bot] Startup Failed: {e}")

    # --- LIFESPAN ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        asyncio.create_task(start_bot_services())
        yield
        try:
            print("🛑 [Bot] Stopping...")
            await tg_bot.stop()
        except:
            pass

    # --- APP ---
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)
    app.include_router(stream_routes.router)

    @app.get("/")
    async def health_check():
        return {"status": "active", "service": "Cloud Manager Bot"}

except Exception as e:
    print(f"❌ [Main] GLOBAL CRASH: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f"🌍 [Web] Starting Server on 0.0.0.0:{port}...")
        
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=port, 
            log_level="info"
        )
    except Exception as e:
        print(f"❌ [Web] Start Error: {e}")
