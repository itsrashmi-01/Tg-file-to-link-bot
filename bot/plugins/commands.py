from pyrogram import Client, filters
from config import Config

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # Check if there is an argument (e.g., /start 105)
    if len(message.command) > 1:
        msg_id = message.command[1]
        # Instead of sending the link again, just send the file directly
        try:
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=Config.LOG_CHANNEL,
                message_id=int(msg_id)
            )
        except Exception as e:
            await message.reply_text(f"Error retrieving file: {e}")
    else:
        await message.reply_text("👋 Send me a file to get a high-speed direct download link!")
