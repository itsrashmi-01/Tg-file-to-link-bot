from pyrogram import Client, filters
from bot.clone import db

@Client.on_message(filters.command("protect") & filters.private & filters.reply)
async def protect_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: Reply to a file with `/protect your_password`")
    
    password = message.command[1]
    target_msg = message.reply_to_message
    
    await message.reply(f"🔒 **Password Set:** `{password}`", quote=True)
    
    media = target_msg.document or target_msg.video or target_msg.audio
    if media:
        await db.files.update_one(
            {"file_unique_id": media.file_unique_id},
            {"$set": {"password": password}},
            upsert=True
        )
