import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.clone import db
from config import Config

# Database Collections
users_col = db.users
auth_codes_col = db.auth_codes

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("login_"):
        token = message.command[1].replace("login_", "")
        result = await auth_codes_col.update_one(
            {"token": token, "status": "pending"},
            {"$set": {
                "status": "verified",
                "user_id": message.from_user.id,
                "user_info": {"id": message.from_user.id, "first_name": message.from_user.first_name},
                "role": "admin" if message.from_user.id in Config.ADMIN_IDS else "user"
            }}
        )
        if result.modified_count > 0:
            await message.reply("✅ **Login Successful!**\n\nYou can now return to your browser.", quote=True)
        else:
            await message.reply("❌ **Link Expired.**", quote=True)
        return

    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except: pass

    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    
    text = (
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "I am a **File Store & Link Generator Bot**.\n"
        "Send me any file to get a direct download link.\n\n"
        "🤖 **Create Clone:**\n"
        "`/clone <bot_token> <channel_id>`\n"
        "_(Make sure the bot is Admin in your channel)_"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("📂 My Files", callback_data="my_files"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")],
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    await message.reply_text(text, reply_markup=buttons, quote=True)

# ... (Keep existing callbacks: settings, toggle_short, start_menu) ...
# Copy the existing callbacks from your previous start.py file here.
# I'll include the important ones for clone_info update:

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "🤖 **Create Your Own Bot**\n\n"
        "1. Create a bot in @BotFather\n"
        "2. Create a Private Channel (for Database)\n"
        "3. Add your new bot to that channel as Admin\n"
        "4. Get the Channel ID (e.g. -100123456789)\n\n"
        "**Command:**\n`/clone <bot_token> <channel_id>`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

# ... (Include other callbacks from previous steps)
@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user = await users_col.find_one({"user_id": user_id})
    is_short = user.get("use_short", False)
    status_text = "✅ ON" if is_short else "❌ OFF"
    toggle_data = "false" if is_short else "true"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔗 Short Link (TinyURL): {status_text}", callback_data=f"toggle_short_{toggle_data}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text("⚙️ **Settings**", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^toggle_short_"))
async def toggle_short_handler(client, callback_query):
    new_status = callback_query.data.split("_")[2] == "true"
    await users_col.update_one({"user_id": callback_query.from_user.id}, {"$set": {"use_short": new_status}}, upsert=True)
    await settings_callback(client, callback_query)

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    await start_handler(client, callback_query.message)
    await callback_query.message.delete()
