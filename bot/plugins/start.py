import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.clone import db
from config import Config

# Database Collections
users_col = db.users
auth_codes_col = db.auth_codes

# --- HELPER: Get Start Menu Content ---
def get_start_menu(first_name):
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    
    separator = "&" if "?" in web_app_url else "?"
    files_url = f"{web_app_url}{separator}tab=files"

    text = (
        f"👋 **Hi {first_name}!**\n\n"
        "I am your personal **File-to-Link** engine.\n"
        "Send me any file, and I'll generate a high-speed direct link for you.\n\n"
        "🚀 **Features:** Streaming, Password Protection, and custom Clone Bots."
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))],
        [
            InlineKeyboardButton("📂 My Files", web_app=WebAppInfo(url=files_url)), 
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")],
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])
    return text, buttons

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 1. LOGIN VERIFICATION (Web Dashboard) ---
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
            return await message.reply("✅ **Login Successful!**\n\nYou can now return to your browser dashboard.", quote=True)

    # --- 2. USER REGISTRATION & STATE RESET ---
    await users_col.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "first_name": message.from_user.first_name,
            "state": "IDLE" # Reset state on /start to prevent getting stuck
        }},
        upsert=True
    )

    text, buttons = get_start_menu(message.from_user.first_name)
    await message.reply_text(text, reply_markup=buttons, quote=True)

# --- CLONE SETUP ENTRY POINT ---

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_handler(client, callback_query):
    """
    Triggers the new interactive flow.
    The logic for 'get_token' and subsequent steps resides in commands.py.
    """
    text = (
        "🤖 **Clone Machine**\n\n"
        "You can create a fully branded version of this bot that uses **your own channel** as storage.\n\n"
        "**Requirements:**\n"
        "1️⃣ A Bot Token from @BotFather\n"
        "2️⃣ A Private Channel (where your files will be stored)\n\n"
        "Ready to set up your personal bot?"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Let's Start", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text(text, reply_markup=buttons)

# --- SETTINGS & NAVIGATION ---

@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    user = await users_col.find_one({"user_id": callback_query.from_user.id})
    is_short = user.get("use_short", False)
    
    status_text = "✅ ON" if is_short else "❌ OFF"
    toggle_data = "false" if is_short else "true"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔗 TinyURL Shortener: {status_text}", callback_data=f"toggle_short_{toggle_data}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    
    await callback_query.message.edit_text(
        "⚙️ **User Settings**\n\nCustomize how your bot generates links below.",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    text, buttons = get_start_menu(callback_query.from_user.first_name)
    await callback_query.message.edit_text(text, reply_markup=buttons)

# ... (rest of about/help handlers remain the same)
