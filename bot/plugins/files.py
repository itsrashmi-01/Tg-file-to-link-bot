from pyrogram import Client, filters
from config import Config

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    try:
        # Forward to Log Channel to get a permanent File ID
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        # --- LOGIC TO SWITCH BETWEEN BLOGGER AND DIRECT LINK ---
        if Config.BLOGGER_URL:
            # If BLOGGER_URL is set in Render, use that format
            # Example: https://your-blog.blogspot.com?id=123
            stream_link = f"{Config.BLOGGER_URL}?id={log_msg.id}"
        else:
            # Otherwise, use the standard direct download link
            # Example: https://your-app.onrender.com/dl/123
            stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        await message.reply_text(
            f"**File Name:** `{message.document.file_name if message.document else 'File'}`\n"
            f"**Download Link:**\n{stream_link}",
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}\nMake sure I am Admin in the Log Channel!")
