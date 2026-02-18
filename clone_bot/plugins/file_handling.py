from pyrogram import Client, filters
from config import Config

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def clone_file_handler(client, message):
    try:
        # Clones forward to the SAME Log Channel so the main server can stream it
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        # Different response format for clones
        await message.reply_text(
            f"🚀 **Fast Download Link Generated!**\n\n"
            f"🔗 [Click Here to Download]({stream_link})\n\n"
            f"This link is powered by the main server.",
            quote=True,
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text("Oops! Something went wrong.")