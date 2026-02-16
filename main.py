import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from bot import bot_client
from web.routes import router as web_router
from config import Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Starting services...")
    await bot_client.start()
    yield
    print("😴 Shutting down...")
    await bot_client.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=Config.PORT)
