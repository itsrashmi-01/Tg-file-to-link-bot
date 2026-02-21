# ... (Keep existing imports)
from bot.clone import db 

files_col = db.files # Access DB

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    # ... (Keep Force Sub logic if you added it) ...

    try:
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        # --- NEW: SAVE TO DB FOR HISTORY ---
        media = message.document or message.video or message.audio
        await files_col.insert_one({
            "user_id": message.from_user.id,
            "log_msg_id": log_msg.id,
            "file_name": getattr(media, "file_name", "file"),
            "file_size": getattr(media, "file_size", 0),
            "file_unique_id": media.file_unique_id,
            "timestamp": message.date
        })
        # -----------------------------------

        if Config.BLOGGER_URL:
            stream_link = f"{Config.BLOGGER_URL}?id={log_msg.id}"
        else:
            stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
            
        await message.reply_text(
            f"**File Name:** `{getattr(media, 'file_name', 'File')}`\n"
            f"**Download Link:**\n{stream_link}",
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
