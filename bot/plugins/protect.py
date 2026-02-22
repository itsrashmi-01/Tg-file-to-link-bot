from pyrogram import Client, filters
from bot.clone import get_db

@Client.on_message(filters.command("protect") & filters.private & filters.reply)
async def protect_handler(client, message):
    if len(message.command) < 2: return await message.reply("Usage: `/protect password` (reply to file)")
    password = message.command[1]
    media = message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio
    
    current_db = get_db(client)
    if media:
        await current_db.files.update_one({"file_unique_id": media.file_unique_id}, {"$set": {"password": password}})
        await message.reply("🔒 Password set!")
