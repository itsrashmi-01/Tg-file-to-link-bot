from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient

db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
clones_col = db.clones

@Client.on_callback_query(filters.regex("clone_manage"))
async def clone_dashboard(client, query):
    user_id = query.from_user.id
    clone = await clones_col.find_one({"user_id": user_id})
    if not clone:
        return await query.answer("❌ No bot found.", show_alert=True)
    
    text = f"🤖 **Bot:** @{clone.get('username')}\n📢 **Log Channel:** `{clone.get('log_channel')}`"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete Bot", callback_data="clone_delete")]])
    await query.message.edit_caption(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("clone_delete"))
async def delete_clone(client, query):
    await clones_col.delete_one({"user_id": query.from_user.id})
    await query.message.edit_caption("✅ Bot Deleted.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="home")]]))