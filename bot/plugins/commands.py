import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.clone import start_clone, clones_col, db # Reusing db from clone.py
from config import Config

users_col = db.users

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # 1. Save User to DB
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

# ... (Keep clone_handler) ...

# --- NEW ADMIN COMMANDS ---

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
