import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import Config
from bot_client import bot
from bot.clone import load_all_clones
from server.stream_routes import router

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/")
async def health(): return {"status": "active"}

async def start():
    print(f"🌍 Starting on Port {Config.PORT}")
    config = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT)
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        bot.start(),
        load_all_clones(),
        server.serve()
    )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start())
