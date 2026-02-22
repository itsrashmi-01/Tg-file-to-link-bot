import os
import sys

# Force output to console
sys.stdout.reconfigure(encoding='utf-8')

print("⏳ [System] Initializing...")

try:
    # 1. Load Config & Check Envs
    from config import Config
    print(f"✅ Config Loaded. Port: {Config.PORT}")
    
    if not Config.API_ID or not Config.API_HASH or not Config.BOT_TOKEN:
        print("❌ CRITICAL: Missing API_ID, API_HASH, or BOT_TOKEN.")
        sys.exit(1)
        
    if not Config.MONGO_URL:
        print("❌ CRITICAL: Missing MONGO_URL.")
        sys.exit(1)

    # 2. Import Libraries
    import asyncio
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    print("✅ Libraries Imported.")

    # 3. Import Bot Modules
    try:
        from bot_client import tg_bot
        from bot.server import auth_routes, stream_routes
        from bot.clone import load_all_clones
        print("✅ Bot Modules Loaded.")
    except Exception as e:
        print(f"❌ [Import Error] Failed to load bot modules: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 4. Background Task
    async def start_bot_services():
        print("🚀 [Bot] Starting Telegram Client...")
        try:
            await tg_bot.start()
            me = await tg_bot.get_me()
            print(f"✅ [Bot] Online as @{me.username}")
            
            print("♻️ [Bot] Loading Clones...")
            await load_all_clones()
            print("✅ [Bot] Clones Loaded.")
        except Exception as e:
            print(f"⚠️ [Bot] Startup Failed: {e}")
            import traceback
            traceback.print_exc()

    # 5. Lifespan
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        asyncio.create_task(start_bot_services())
        yield
        try:
            print("🛑 [Bot] Stopping...")
            await tg_bot.stop()
        except:
            pass

    # 6. App Setup
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
    print(f"❌ [Global Crash] {e}")
    sys.exit(1)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌍 [Web] Starting Server on 0.0.0.0:{port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
