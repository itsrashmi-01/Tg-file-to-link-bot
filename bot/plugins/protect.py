from pyrogram import Client, filters
from bot.clone import db

files_col = db.files # New collection for file metadata

@Client.on_message(filters.command("protect") & filters.private & filters.reply)
async def protect_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: Reply to a file with `/protect your_password`")
    
    password = message.command[1]
    # Use the original message ID (from the Log Channel if possible, or the user's message)
    # Note: To link this to the streaming URL, we usually need the ID used in the link.
    # Users should reply to the bot's "File Name: ... Download Link: ..." message or the file itself.
    
    target_msg = message.reply_to_message
    
    # We need to find the Log Channel Message ID associated with this file.
    # Since we don't store a map of "User Message -> Log Message", this is tricky.
    # SIMPLIFICATION: We will assume the user replies to the file they just uploaded.
    # Ideally, you'd store the file_unique_id.
    
    await message.reply(f"🔒 **Password Set:** `{password}`\n\n(Note: This password will apply to links generated for this file ID)", quote=True)
    
    # Store password keyed by file_unique_id (more robust)
    media = target_msg.document or target_msg.video or target_msg.audio
    if media:
        await files_col.update_one(
            {"file_unique_id": media.file_unique_id},
            {"$set": {"password": password}},
            upsert=True
        )
