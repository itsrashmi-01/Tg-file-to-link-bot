from pyrogram import Client, filters
from bot.clone import clones_col

@Client.on_message(filters.command("connect") & filters.channel)
async def connect_db(client, message):
    user_id = getattr(client, "owner_id", None)
    if not user_id: return

    channel_id = message.chat.id
    await clones_col.update_one(
        {"user_id": user_id},
        {"$set": {"log_channel": channel_id}}
    )
    client.log_channel = channel_id
    await message.reply(f"✅ **Database Linked!**\nID: `{channel_id}`")
