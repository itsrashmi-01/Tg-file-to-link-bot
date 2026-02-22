import os
import sys
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Output buffering fix
sys.stdout.reconfigure(encoding='utf-8')

BOT_STATUS = "Starting..."
STARTUP_LOGS = []

try:
    from config import Config
    from bot_client import tg_bot
    from bot.server import auth_routes, stream_routes
    from bot.clone import load_all_clones
    
    async def start_bot_services():
        global BOT_STATUS
        try:
            print("🚀 Starting Bot...")
            await tg_bot.start()
            print("✅ Bot Started")
            await load_all_clones()
            BOT_STATUS = "Running"
        except Exception as e:
            print(f"❌ BOT CRASH: {e}")
            BOT_STATUS = f"Failed: {e}"
            STARTUP_LOGS.append(str(e))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        asyncio.create_task(start_bot_services())
        yield
        try: await tg_bot.stop()
        except: pass

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(auth_routes.router)
    app.include_router(stream_routes.router)

    @app.get("/")
    def index():
        return {"status": BOT_STATUS, "logs": STARTUP_LOGS}

except Exception as e:
    print(f"❌ IMPORT CRASH: {e}")
    # Fallback App if imports fail
    app = FastAPI()
    @app.get("/")
    def crash_report():
        return {"status": "CRASHED", "error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌍 Starting Server on {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
