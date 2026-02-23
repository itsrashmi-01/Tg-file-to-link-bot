import asyncio
import uvicorn
from fastapi import FastAPI
from bot_client import tg_bot
from bot.clone import load_all_clones
from bot.server.stream_routes import router as stream
from bot.server.auth_routes import router as auth

app = FastAPI()
app.include_router(stream)
app.include_router(auth)

async def start():
    await tg_bot.start()
    await load_all_clones()
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start())
