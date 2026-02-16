from pyrogram import Client, filters
from database.users import user_db
from config import Config
import asyncio

@Client.on_message(filters.command("stats") & filters.user(Config.ADMINS))
async def stats(client, message):
    count = await user_db.get_stats()
    await message.reply(f"📊 **Total Users:** `{count}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMINS))
async def broadcast(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast.")
    
    msg = await message.reply("🚀 Sending...")
    users = await user_db.get_all_users()
    sent = 0
    async for user in users:
        try:
            await message.reply_to_message.copy(user["_id"])
            sent += 1
            await asyncio.sleep(0.1)
        except: pass
        
    await msg.edit_text(f"✅ **Broadcast Done!** Sent to `{sent}` users.")