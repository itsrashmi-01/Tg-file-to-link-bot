from pyrogram import Client, filters
from config import Config
from bot.clone import db
from bot.utils import get_tinyurl

files_col = db.files

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def main_files(client, message):
    log_channel = Config.LOG_CHANNEL_ID
    media = message.document or message.video or message.audio
    
    # Copy to Main Log
    log_msg = await message.copy(log_channel)
    
    await files_col.insert_one({
        "user_id": message.from_user.id,
        "log_msg_id": log_msg.id,
        "channel_id": log_channel,
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "file_unique_id": media.file_unique_id
    })
    
    link = f"{Config.BASE_URL}/dl/{log_msg.id}"
    await message.reply(f"✅ **Main Bot Link:**\n{link}")
