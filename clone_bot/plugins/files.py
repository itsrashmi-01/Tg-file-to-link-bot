from pyrogram import Client, filters
from bot.clone import db

files_col = db.files

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def clone_files(client, message):
    log_channel = getattr(client, "log_channel", None)
    if not log_channel:
        return await message.reply("❌ Use `/connect` in your log channel first.")

    media = message.document or message.video or message.audio
    log_msg = await message.copy(log_channel)
    
    await files_col.insert_one({
        "user_id": message.from_user.id,
        "log_msg_id": log_msg.id,
        "channel_id": log_channel,
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "file_unique_id": media.file_unique_id
    })
    
    await message.reply(f"✅ **Clone Link:**\n{Config.BASE_URL}/dl/{log_msg.id}")
