import base64
from pyrogram import Client, filters
from config import Config
from bot.database.mongodb import db

# Added more filters to ensure it catches different types
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def handle_conversion(client, message):
    print(f"Received file from {message.from_user.id}") # DEBUG
    
    try:
        # 1. Forward to Log Channel
        log_msg = await message.forward(Config.LOG_CHANNEL)
        print(f"Forwarded to log channel: {log_msg.id}") # DEBUG
        
        # 2. Get File ID
        file = message.document or message.video or message.audio or (message.photo[-1] if message.photo else None)
        file_id = file.file_id
        
        # 3. Save to DB
        file_key = await db.save_file(file_id, log_msg.id)
        print(f"Saved to DB with key: {file_key}") # DEBUG
        
        # 4. Create Link
        me = await client.get_me()
        share_link = f"https://t.me/{me.username}?start={file_key}"
        
        await message.reply_text(
            f"**File Stored!**\n\n`{share_link}`",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Error in handler: {e}") # This will show the error in Render logs
        await message.reply_text(f"An error occurred: {e}")
