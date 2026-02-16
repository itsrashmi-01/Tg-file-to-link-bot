import asyncio, uvicorn
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
    print(f"🌍 Starting Server on {Config.PORT}...")
    cfg = uvicorn.Config(app, host="0.0.0.0", port=Config.PORT, timeout_keep_alive=60)
    server = uvicorn.Server(cfg)
    
    asyncio.create_task(bot.start())
    asyncio.create_task(load_all_clones())
    
    await server.serve()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start())