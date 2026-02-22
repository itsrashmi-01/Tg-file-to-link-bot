from pyrogram import Client, filters
from pyrogram.types import Message
from bot.clone import clones_col
from config import Config

# This command runs inside the Clone Bot (and Main Bot, but we filter)
@Client.on_message(filters.command("connect") & filters.channel)
async def connect_channel_handler(client: Client, message: Message):
    try:
        # 1. Identify who is running this (Main Bot or Clone)
        me = await client.get_me()
        
        # 2. Get the owner of this bot from memory or DB
        # For Main Bot, we ignore this command
        if client.name == "pyrogram": # Default name for main session usually, or check ID
             return # Main bot doesn't need this
             
        # In start_clone, we set client.owner_id. Check if it exists.
        if not hasattr(client, 'owner_id'):
            return 

        user_id = client.owner_id
        channel_id = message.chat.id
        channel_title = message.chat.title

        # 3. Check Permissions (Can we write?)
        # If we received the command, we are likely admin, but let's try replying.
        try:
            status_msg = await message.reply_text("🔄 **Connecting...**")
        except:
            # If we can't reply, we can't confirm.
            return 

        # 4. Update Database
        await clones_col.update_one(
            {"user_id": user_id},
            {"$set": {"log_channel": channel_id}}
        )
        
        # 5. Update Running Client Session
        client.log_channel = channel_id

        await status_msg.edit_text(
            f"✅ **Database Connected Successfully!**\n\n"
            f"**Channel:** {channel_title}\n"
            f"**ID:** `{channel_id}`\n\n"
            f"🚀 **Bot is ready.** Send files to me directly to start."
        )

    except Exception as e:
        print(f"Connect Error: {e}")
