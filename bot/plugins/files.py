from pyrogram import Client, filters
from config import Config

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def main_file_handler(client, message):
    try:
        # Forward to Log Channel
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        await message.reply_text(
            f"**File Name:** `{message.document.file_name if message.document else 'File'}`\n"
            f"**Direct Link:**\n{stream_link}",
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"Error: {e}")