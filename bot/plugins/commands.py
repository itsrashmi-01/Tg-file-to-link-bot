from pyrogram import Client, filters
from bot.database.mongodb import db
from config import Config

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    text = message.text.split()
    
    # If it's a deep link (e.g., /start 123)
    if len(text) > 1:
        file_id = text[1]
        data = await db.get_file(file_id)
        
        if data:
            # Copy file from Log Channel to User
            await client.copy_message(
                chat_id=message.from_user.id,
                from_chat_id=Config.LOG_CHANNEL,
                message_id=int(data["_id"])
            )
        else:
            await message.reply_text("Link expired or invalid.")
    else:
        await message.reply_text("Send me any file and I'll give you a permanent link!")