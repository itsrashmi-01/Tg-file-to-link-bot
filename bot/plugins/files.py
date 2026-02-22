from pyrogram import Client, filters
from config import Config
from bot.clone import db

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_files(client, message):
    media = message.document or message.video or message.audio
    # Forward to log channel for permanent file_id
    log_msg = await message.forward(Config.LOG_CHANNEL)
    
    file_data = {
        "user_id": message.from_user.id,
        "file_name": media.file_name,
        "file_size": media.file_size,
        "file_id": media.file_id,
        "log_msg_id": log_msg.id,
        "password": None
    }
    
    res = await db.files.insert_one(file_data)
    link = f"{Config.DOMAIN}/dl/{res.inserted_id}"
    await message.reply(f"✅ **File Stored!**\n\nLink: `{link}`")
