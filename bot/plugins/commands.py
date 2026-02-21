import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users
auth_codes_col = db.auth_codes

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 1. CHECK FOR LOGIN VERIFICATION ---
    if len(message.command) > 1:
        payload = message.command[1]
        
        if payload.startswith("login_"):
            token = payload.replace("login_", "")
            
            # Find the pending token and verify it
            result = await auth_codes_col.update_one(
                {"token": token, "status": "pending"},
                {"$set": {
                    "status": "verified",
                    "user_id": message.from_user.id,
                    "user_info": {
                        "id": message.from_user.id,
                        "first_name": message.from_user.first_name,
                        "username": message.from_user.username or ""
                    },
                    "role": "admin" if message.from_user.id in Config.ADMIN_IDS else "user"
                }}
            )
            
            if result.modified_count > 0:
                await message.reply("✅ **Login Successful!**\n\nYou can now return to your browser.", quote=True)
            else:
                await message.reply("❌ **Link Expired or Already Used.**", quote=True)
            return

    # --- 2. EXISTING START LOGIC ---
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except Exception:
        pass

    await message.reply_text(
        "**Welcome!**\n\n"
        "Send me any file to get a link.\n"
        "Features:\n"
        "• `/clone bot_token` - Create your own bot\n"
        "• `/protect password` - Reply to a file to set a password",
        quote=True
    )

@Client.on_message(filters.command("clone") & filters.private)
async def clone_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/clone bot_token`")
    
    token = message.command[1]
    msg = await message.reply("♻️ Cloning...")
    
    try:
        new_client = await start_clone(token)
        await clones_col.insert_one({"token": token, "user_id": message.from_user.id})
        await msg.edit(f"✅ **Cloned Successfully!**\nBot: @{new_client.me.username}")
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
