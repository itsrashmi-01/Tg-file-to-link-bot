from pyrogram import filters
from pyrogram.handlers import MessageHandler
from database.files_db import files_db
from config import Config

async def save_fn(client, message):
    # Security: Only Owner
    if message.from_user.id != client.OWNER_ID:
        return

    try:
        # Forward to Log Channel
        log_msg = await message.forward(client.LOG_CHANNEL)
        
        # Extract File Info
        media = log_msg.document or log_msg.video or log_msg.audio or log_msg.photo
        if isinstance(media, list): media = media[-1]
        
        # Save to DB
        file_hash = await files_db.save_file(
            client.BOT_ID,
            media.file_id,
            getattr(media, "file_name", "file"),
            getattr(media, "mime_type", "application/octet-stream")
        )

        await message.reply_text(
            f"✅ **Saved!**\n"
            f"🔗 `{Config.BASE_URL}/dl/{client.BOT_ID}/{file_hash}`"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Trigger on any media file
file_handler = MessageHandler(save_fn, (filters.document | filters.video | filters.audio) & filters.private)