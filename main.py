import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from pyrogram import Client, idle
from config import Config
from database.main_db import main_db
from database.files_db import files_db
from core.clone_manager import CloneManager, RUNNING_BOTS

# --- WEB SERVER ---
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Active", "bots_running": len(RUNNING_BOTS)}

@app.get("/dl/{bot_id}/{file_hash}")
async def stream_handler(bot_id: str, file_hash: str):
    client = CloneManager.get_client(bot_id)
    if not client:
        return Response("Bot not active", status_code=404)
    
    file_data = await files_db.get_file(bot_id, file_hash)
    if not file_data:
        return Response("File not found", status_code=404)

    async def generate():
        stream = client.stream_media(file_data["file_id"])
        async for chunk in stream:
            yield chunk

    return StreamingResponse(
        generate(),
        media_type=file_data["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'}
    )

# --- MOTHER BOT ---
# We use Pyrogram's 'plugins' system for the mother bot to keep main.py clean
MotherBot = Client(
    "MotherBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins") # Automatically loads plugins/start.py, plugins/admin.py
)

# --- LIFECYCLE ---
@app.on_event("startup")
async def startup():
    print("Starting Mother Bot...")
    await MotherBot.start()
    
    print("Reviving Clones...")
    async for clone in await main_db.get_all_clones():
        await CloneManager.start_clone(clone["token"], clone["channel_id"], clone["owner_id"])

# Run with: uvicorn main:app --host 0.0.0.0 --port 10000