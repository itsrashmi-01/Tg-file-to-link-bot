import asyncio
import uvicorn
from bot_client import tg_bot
from bot.clone import load_all_clones
from bot.server.stream_routes import router as stream
from bot.server.auth_routes import router as auth
from fastapi import FastAPI

app = FastAPI()
app.include_router(stream)
app.include_router(auth)

async def start_services():
    # Start the bot
    await tg_bot.start()
    # Load clones
    await load_all_clones()
    
    # Setup and run the server
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start_services())
