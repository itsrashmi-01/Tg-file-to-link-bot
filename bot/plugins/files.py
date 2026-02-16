from pyrogram import Client, filters
from config import Config
from database.files import file_db

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_incoming_file(client, message):
    editable = await message.reply("🔄 Processing...")
    
    # 1. Store permanently in Log Channel
    log_msg = await message.copy(Config.LOG_CHANNEL)
    media = getattr(log_msg, log_msg.media.value)
    
    # 2. Save Metadata
    data = {
        "file_id": media.file_id,
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "mime_type": getattr(media, "mime_type", "application/octet-stream")
    }
    
    slug = await file_db.add_file(data)
    
    # 3. Create Link for Blogger
    link = f"{Config.BLOG_URL}?id={slug}"
    await editable.edit(f"✅ **Link Generated!**\n\n`{data['file_name']}`\n\n🔗 {link}")
