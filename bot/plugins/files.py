from pyrogram import Client, filters
from config import Config

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    try:
        # Forward to Log Channel to get a permanent File ID
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        # Generate Link (Points to FastAPI Stream Route)
        # We use log_msg.id so we can find it in the channel later
        stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        await message.reply_text(
            f"**File Name:** `{message.document.file_name if message.document else 'File'}`\n"
            f"**Download Link:**\n{stream_link}",
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}\nMake sure I am Admin in the Log Channel!")