from pyrogram import Client, filters
from core.clone_manager import CloneManager
from database.main_db import main_db

@Client.on_message(filters.command("clone") & filters.private)
async def clone_cmd(client, message):
    try:
        _, token, channel = message.text.split()
    except:
        return await message.reply_text("Usage: `/clone [TOKEN] [CHANNEL_ID]`")

    msg = await message.reply_text("♻️ Processing...")
    
    success = await CloneManager.start_clone(token, channel, message.from_user.id)
    
    if success:
        await main_db.add_clone(token, channel, message.from_user.id)
        await msg.edit_text("✅ **Bot Cloned Successfully!**")
    else:
        await msg.edit_text("❌ Failed. Check Token/Channel.")