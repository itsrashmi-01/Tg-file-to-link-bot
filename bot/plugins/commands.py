import asyncio
from pyrogram import Client, filters
from bot.clone import start_clone, stop_clone, clones_col, db
from config import Config

users_col = db.users

# --- CLONE MANAGEMENT ---

@Client.on_message(filters.command("clone") & filters.private)
async def clone_handler(client, message):
    """
    Handles the creation of a new bot clone using user-provided token and log channel.
    """
    # Check arguments: /clone <token> <channel_id>
    if len(message.command) < 3:
        return await message.reply(
            "⚠️ **Setup Instructions:**\n\n"
            "1. Create a bot in @BotFather and get the **Token**.\n"
            "2. Create a **Private Channel** (this will be your database).\n"
            "3. Add your new bot to that channel as an **Admin**.\n"
            "4. Get your Channel ID (e.g., -100xxxx).\n\n"
            "👉 **Usage:** `/clone <bot_token> <channel_id>`"
        )
    
    token = message.command[1]
    user_id = message.from_user.id
    
    try:
        channel_id = int(message.command[2])
    except ValueError:
        return await message.reply("❌ **Error:** Channel ID must be an integer (starts with -100).")

    # 1. Check if user already has an active clone
    existing = await clones_col.find_one({"user_id": user_id})
    if existing:
        return await message.reply(
            f"❌ **You already have a clone:** @{existing.get('username')}\n"
            "Delete the existing one before creating a new one."
        )

    status_msg = await message.reply("♻️ **Verifying Token & Channel Permissions...**")
    
    try:
        # 2. Start the clone (this injects client.log_channel and client.owner_id)
        new_client = await start_clone(token, user_id, channel_id)
        
        if new_client and new_client.me:
            # 3. Verify the bot is Admin in the provided channel
            try:
                test = await new_client.send_message(
                    channel_id, 
                    "✅ **Database Connection Successful!**\n\nThis channel is now linked to your bot instance."
                )
            except Exception as e:
                await stop_clone(user_id) # Stop the unauthorized client
                return await status_msg.edit(
                    f"❌ **Permission Denied!**\n\nYour bot (@{new_client.me.username}) must be an **Admin** in the channel `{channel_id}`.\n\nError: `{e}`"
                )

            # 4. Save clone metadata to MongoDB
            await clones_col.insert_one({
                "token": token, 
                "user_id": user_id, 
                "username": new_client.me.username,
                "log_channel": channel_id,
                "created_at": message.date
            })
            
            await status_msg.edit(
                f"✅ **Cloned Successfully!**\n\n"
                f"🤖 **Bot:** @{new_client.me.username}\n"
                f"📂 **Log Channel:** `{channel_id}`\n\n"
                f"You can now send files to @{new_client.me.username} to generate links."
            )
        else:
            await status_msg.edit("❌ **Error:** Could not start the bot. Please check if the token is valid.")
            
    except Exception as e:
        await status_msg.edit(f"❌ **Unexpected Error:** {e}")

@Client.on_message(filters.command("delete_clone") & filters.private)
async def delete_clone_handler(client, message):
    """Allows users to manually shut down and delete their bot instance."""
    user_id = message.from_user.id
    clone = await clones_col.find_one({"user_id": user_id})
    
    if not clone:
        return await message.reply("❌ You don't have an active clone bot.")

    msg = await message.reply("🗑️ **Shutting down your bot instance...**")
    
    try:
        await stop_clone(user_id)
        await clones_col.delete_one({"user_id": user_id})
        await msg.edit("✅ **Clone Deleted Successfully.**\nYou can now create a new one using `/clone`.")
    except Exception as e:
        await msg.edit(f"❌ Error during deletion: {e}")

# --- ADMIN & UTILITY COMMANDS ---

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message):
    """Admin only: View system-wide usage."""
    users = await users_col.count_documents({})
    clones = await clones_col.count_documents({})
    await message.reply_text(
        f"**📊 System Statistics**\n\n"
        f"👤 **Total Users:** `{users}`\n"
        f"🤖 **Active Clones:** `{clones}`"
    )

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_IDS) & filters.reply)
async def broadcast_handler(client, message):
    """Admin only: Send a message to all registered users."""
    msg = await message.reply("📡 **Broadcasting...**")
    count = 0
    async for user in users_col.find():
        try:
            # Using copy for safety (avoids forwarding tags)
            await message.reply_to_message.copy(chat_id=user['user_id'])
            count += 1
            await asyncio.sleep(0.05) # Rate limiting to avoid flood
        except Exception:
            pass # Skip users who blocked the bot
            
    await msg.edit(f"✅ **Broadcast Complete!**\nDelivered to `{count}` users.")
