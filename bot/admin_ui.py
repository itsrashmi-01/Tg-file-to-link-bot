from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
import datetime

main_db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
users_col = main_db.large_file_users
files_col = main_db.large_files
clones_col = main_db.clones

@Client.on_message(filters.command("admin") & filters.user(Config.OWNER_ID) & filters.private)
async def admin_panel(client, message):
    total_users = await users_col.count_documents({})
    premium = await users_col.count_documents({"plan_type": "premium"})
    
    text = (
        f"👑 **Super Admin**\n"
        f"👥 Users: `{total_users}`\n"
        f"💎 Premium: `{premium}`"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Refresh", callback_data="admin_refresh")]
    ])
    await message.reply_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("admin_refresh"))
async def refresh_stats(client, query):
    if query.from_user.id == Config.OWNER_ID:
        await admin_panel(client, query.message)

@Client.on_message(filters.command("addprem") & filters.user(Config.OWNER_ID))
async def add_premium(client, message):
    try:
        _, uid, days = message.text.split()
        exp = datetime.datetime.now() + datetime.timedelta(days=int(days))
        await users_col.update_one({"_id": int(uid)}, {"$set": {"plan_type": "premium", "plan_expiry": exp}}, upsert=True)
        await message.reply_text(f"✅ Premium added to {uid} for {days} days.")
    except:
        await message.reply_text("Use: /addprem ID DAYS")