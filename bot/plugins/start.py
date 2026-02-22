import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.clone import db, clones_col, stop_clone
from config import Config

# Database Collections
users_col = db.users
auth_codes_col = db.auth_codes

# --- HELPER: Get Start Menu Content (Now Async) ---
async def get_start_menu(user_id, first_name):
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    
    # Logic to append query parameter safely
    separator = "&" if "?" in web_app_url else "?"
    files_url = f"{web_app_url}{separator}tab=files"

    text = (
        f"👋 **Hi {first_name}!**\n\n"
        "I am a **File Store & Link Generator Bot**.\n"
        "Send me any file to get a direct download link.\n\n"
        "⚙️ **New:** Go to **Settings** to turn on/off TinyURL shortener."
    )

    # --- CHECK FOR EXISTING CLONE ---
    user_bot = await clones_col.find_one({"user_id": user_id})
    
    if user_bot:
        # If user has a bot -> Show "Manage"
        clone_btn = InlineKeyboardButton("🤖 Manage Your Bot", callback_data="manage_clone")
    else:
        # If no bot -> Show "Create"
        clone_btn = InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))],
        [
            InlineKeyboardButton("📂 My Files", web_app=WebAppInfo(url=files_url)), 
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [clone_btn], # Dynamic Button
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])
    return text, buttons

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 1. LOGIN VERIFICATION ---
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
            await message.reply("✅ **Login Successful!**\n\nReturn to your browser.", quote=True)
        else:
            await message.reply("❌ **Link Expired.**", quote=True)
        return

    # --- 2. MAIN START MENU ---
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except: pass

    # Await the async menu generator
    text, buttons = await get_start_menu(message.from_user.id, message.from_user.first_name)
    await message.reply_text(text, reply_markup=buttons, quote=True)

# --- MANAGE CLONE HANDLER ---

@Client.on_callback_query(filters.regex("manage_clone"))
async def manage_clone_handler(client, callback_query):
    user_id = callback_query.from_user.id
    user_bot = await clones_col.find_one({"user_id": user_id})
    
    if not user_bot:
        await callback_query.answer("⚠️ Bot not found!", show_alert=True)
        return await back_to_start(client, callback_query)

    username = user_bot.get('username', 'Unknown')
    token_masked = user_bot.get('token', '******')[:10] + "..."
    
    text = (
        f"🤖 **Your Clone Bot Manager**\n\n"
        f"👤 **Name:** {user_bot.get('first_name', 'Unknown')}\n"
        f"🔗 **Username:** @{username}\n"
        f"🆔 **Log Channel:** `{user_bot.get('log_channel')}`\n"
        f"🔑 **Token:** `{token_masked}`\n\n"
        f"__What would you like to do?__"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Delete Bot", callback_data="delete_clone_confirm")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("delete_clone_confirm"))
async def delete_clone_confirm_handler(client, callback_query):
    user_id = callback_query.from_user.id
    
    # Stop the running bot instance
    await stop_clone(user_id)
    
    # Remove from DB
    await clones_col.delete_one({"user_id": user_id})
    
    await callback_query.answer("✅ Bot deleted successfully!", show_alert=True)
    await back_to_start(client, callback_query)

# --- SETTINGS & TOGGLE LOGIC ---

@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user = await users_col.find_one({"user_id": user_id})
    
    # Default is False (OFF)
    is_short = user.get("use_short", False)
    
    status_text = "✅ ON" if is_short else "❌ OFF"
    toggle_data = "false" if is_short else "true"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔗 Short Link (TinyURL): {status_text}", callback_data=f"toggle_short_{toggle_data}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    
    await callback_query.message.edit_text(
        "⚙️ **User Settings**\n\n"
        "Here you can customize your bot experience.\n"
        "Toggle **Short Link** to automatically shorten your URLs using TinyURL.",
        reply_markup=buttons
    )

@Client.on_callback_query(filters.regex(r"^toggle_short_"))
async def toggle_short_handler(client, callback_query):
    new_status = callback_query.data.split("_")[2] == "true"
    
    await users_col.update_one(
        {"user_id": callback_query.from_user.id},
        {"$set": {"use_short": new_status}},
        upsert=True
    )
    
    # Refresh the settings menu to show new status
    await settings_callback(client, callback_query)

# --- BACK BUTTON HANDLER ---

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    
    # Await the async menu generator
    text, buttons = await get_start_menu(user_id, first_name)
    await callback_query.message.edit_text(text, reply_markup=buttons)

# --- INFO HANDLERS ---

@Client.on_callback_query(filters.regex("help"))
async def help_handler(client, callback_query):
    text = (
        "❓ **Help Guide**\n\n"
        "1. **Send File:** Send any file to the bot.\n"
        "2. **Get Link:** The bot replies with a download link.\n"
        "3. **Streaming:** You can watch videos directly without downloading.\n"
        "4. **Batch:** Send an album (multiple files) to get a batch link."
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    await callback_query.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("about"))
async def about_handler(client, callback_query):
    text = (
        "ℹ️ **About Bot**\n\n"
        "This bot is a high-speed Telegram File-to-Link converter.\n"
        "It supports **Resume Capabilities**, **Streaming**, and **Password Protection**."
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    await callback_query.message.edit_text(text, reply_markup=buttons)

# Note: The 'clone_info' handler is now managed in bot/plugins/clone_chat.py
# If you haven't added that file yet, ensure you add a placeholder or the full file.
