import os
import asyncio
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
import secrets

# --- CONFIGURATION (Load from Env Vars) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL")) # Channel ID where files are stored
MONGO_URI = os.environ.get("MONGO_URI")
# Render provides the URL automatically, but we need to know it to generate links
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["file2link_db"]
collection = db["files"]

# --- BOT & SERVER SETUP ---
app = FastAPI()
bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- HELPER FUNCTIONS ---
def generate_hash():
    return secrets.token_urlsafe(8)

async def get_file_by_hash(file_hash):
    return await collection.find_one({"_id": file_hash})

# --- BOT HANDLERS ---
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("Send me any file, video, or audio, and I'll generate a direct download link!")

@bot.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def file_handler(client, message):
    # 1. Forward to Log Channel to keep a permanent copy
    try:
        log_msg = await message.forward(LOG_CHANNEL)
    except Exception as e:
        await message.reply_text(f"Error: Could not forward to log channel. Make sure I am Admin there.\n{e}")
        return

    # 2. Get the file_id from the forwarded message
    file_id = log_msg.document or log_msg.video or log_msg.audio or log_msg.photo
    # Photos are a list, get the largest one
    if hasattr(file_id, "file_id"):
        file_id = file_id.file_id
    else:
        file_id = file_id[-1].file_id # For photos

    # 3. Save to DB
    file_hash = generate_hash()
    await collection.insert_one({
        "_id": file_hash,
        "file_id": file_id,
        "file_name": getattr(log_msg.document, "file_name", "file"),
        "mime_type": getattr(log_msg.document, "mime_type", "application/octet-stream")
    })

    # 4. Generate Link
    link = f"{BASE_URL}/dl/{file_hash}"
    await message.reply_text(f"**Here is your link:**\n{link}")

# --- WEB SERVER ROUTES ---
@app.get("/")
async def root():
    return {"status": "Bot is running"}

@app.get("/dl/{file_hash}")
async def stream_file(file_hash: str):
    file_data = await get_file_by_hash(file_hash)
    if not file_data:
        return Response("File not found", status_code=404)

    # Use Pyrogram's `download_media` as a generator isn't natively exposed for streaming 
    # simply in high-level methods, so we use a custom chunk generator via `client.stream_media`
    # Note: `stream_media` is a Pyrogram feature useful here.
    
    async def file_streamer():
        # We need a new client session for the web request or use the existing bot instance
        # Streaming directly from Telegram servers
        stream = bot.stream_media(file_data["file_id"])
        async for chunk in stream:
            yield chunk

    return StreamingResponse(
        file_streamer(),
        media_type=file_data["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'}
    )

# --- STARTUP ---
# We need to run the bot in the background when FastAPI starts
@app.on_event("startup")
async def startup_event():
    await bot.start()

@app.on_event("shutdown")
async def shutdown_event():
    await bot.stop()
