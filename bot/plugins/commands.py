import asyncio
from pyrogram import Client, filters
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users

# --- ADMIN & UTILITY COMMANDS ---

@Client.on_message(filters.command("clone") & filters.private)
async def clone_handler(client, message):
    # Check arguments: /clone <token> <channel_id>
    if len(message.command) < 3:
        return await message.reply(
            "⚠️ **Usage:**\n`/clone <bot_token> <channel_id>`\n\n"
            "1. Create a bot in @BotFather\n"
            "2. Create a Private Channel\n"
            "3. Add your new bot to that channel as Admin\n"
            "4. Get Channel ID (e.g., -100xxxx)\n"
            "5. Send the command here."
        )
    
    token = message.command[1]
    try:
        channel_id = int(message.command[2])
    except ValueError:
        return await message.reply("❌ **Error:** Channel ID must be an integer (e.g., -100123456789)")

    msg = await message.reply("♻️ Cloning and verifying...")
    
    try:
        # Check if user already has a clone (Optional: Limit 1 per user)
        # existing = await clones_col.find_one({"user_id": message.from_user.id})
        # if existing: return await msg.edit("❌ You already have a clone bot. Use the dashboard to manage it.")

        new_client = await start_clone(token, message.from_user.id, channel_id)
        
        if new_client and new_client.me:
            # Verify Channel Access
            try:
                test = await new_client.send_message(channel_id, "✅ **Database Connected!**")
                # await test.delete() # Optional cleanup
            except Exception as e:
                await new_client.stop()
                return await msg.edit(f"❌ **Error:** Your bot cannot send messages to that channel.\nMake sure the bot is an **Admin** in the channel.\n\nError: `{e}`")

            # Save to DB
            await clones_col.insert_one({
                "token": token, 
                "user_id": message.from_user.id, 
                "username": new_client.me.username,
                "log_channel": channel_id # Save Channel ID
            })
            
            await msg.edit(f"✅ **Cloned Successfully!**\nBot: @{new_client.me.username}\nDatabase: `{channel_id}`")
        else:
            await msg.edit("❌ **Error:** Could not start the cloned bot. Check the token.")
            
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message):
    users = await users_col.count_documents({})
    clones = await clones_col.count_documents({})
    await message.reply_text(f"**📊 Bot Stats**\n\nUsers: {users}\nClones: {clones}")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_IDS) & filters.reply)
async def broadcast_handler(client, message):
    msg = await message.reply("📡 Broadcasting...")
    count = 0
    async for user in users_col.find():
        try:
            await message.reply_to_message.copy(chat_id=user['user_id'])
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            pass
    await msg.edit(f"✅ Broadcast complete to {count} users.")
