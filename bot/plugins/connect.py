from pyrogram import Client, filters
from pyrogram.types import Message
from bot.clone import clones_col
from config import Config

# This command runs inside the Clone Bot
@Client.on_message(filters.command("connect") & filters.channel)
async def connect_channel_handler(client: Client, message: Message):
    try:
        # 1. Identify who is running this (Main Bot or Clone)
        if client.name == "FastStreamBot": # Ignore Main Bot
             return 
             
        # Check if owner_id exists (set in start_clone)
        if not hasattr(client, 'owner_id'):
            return 

        user_id = client.owner_id
        channel_id = message.chat.id
        channel_title = message.chat.title

        # 2. Check Permissions (Can we write?)
        try:
            status_msg = await message.reply_text("🔄 **Connecting Database...**")
        except:
            # If we can't reply, we likely aren't admin or lack rights
            return 

        # 3. Update Database
        await clones_col.update_one(
            {"user_id": user_id},
            {"$set": {"log_channel": channel_id}}
        )
        
        # 4. Update Running Client Session
        client.log_channel = channel_id

        await status_msg.edit_text(
            f"✅ **Database Connected Successfully!**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**ID:** `{channel_id}`\n\n"
            f"🚀 **Your Clone Bot is Ready.**\n"
            f"Send files to me directly to start generating links."
        )

    except Exception as e:
        print(f"Connect Error: {e}")
