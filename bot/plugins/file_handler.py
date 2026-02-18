import base64
from pyrogram import Client, filters
from config import Config
from bot.database.mongodb import db

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_conversion(client, message):
    # 1. Forward to Log Channel
    log_msg = await message.forward(Config.LOG_CHANNEL)
    
    # 2. Save to DB (using the log message ID as our unique key)
    file_key = await db.save_file(message.document.file_id if message.document else message.video.file_id, log_msg.id)
    
    # 3. Create Link
    bot_username = (await client.get_me()).username
    share_link = f"https://t.me/{bot_username}?start={file_key}"
    
    await message.reply_text(
        f"**File Stored Successfully!**\n\n**Link:** `{share_link}`",
        disable_web_page_preview=True
    )