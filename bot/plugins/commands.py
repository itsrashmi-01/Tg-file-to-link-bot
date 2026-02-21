import asyncio
from pyrogram import Client, filters
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users

# --- ADMIN & UTILITY COMMANDS ONLY ---
# (The /start command has been moved to start.py)

@Client.on_message(filters.command("clone") & filters.private)
async def clone_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/clone bot_token`")
    
    token = message.command[1]
    msg = await message.reply("♻️ Cloning...")
    
    try:
        new_client = await start_clone(token, message.from_user.id)
        if new_client:
            await clones_col.insert_one({
                "token": token, 
                "user_id": message.from_user.id, 
                "username": new_client.username
            })
            await msg.edit(f"✅ **Cloned Successfully!**\nBot: @{new_client.username}")
        else:
            await msg.edit("❌ **Error:** Could not start the clone. Check the token.")
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
            await asyncio.sleep(0.05) # Prevent FloodWait
        except Exception:
            pass
    await msg.edit(f"✅ Broadcast complete to {count} users.")
