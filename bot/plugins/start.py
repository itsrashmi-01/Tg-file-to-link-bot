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
    # --- 1. CHECK FOR LOGIN VERIFICATION (Web App Login) ---
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

    # --- 2. STANDARD START MESSAGE ---
    # Save User to DB
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except Exception:
        pass

    # Ensure we have a valid URL for the Web App button
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL

    # Welcome Text
    text = (
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "I am a **File Store & Link Generator Bot**.\n"
        "Send me any file to get a direct download link.\n\n"
        "**Features:**\n"
        "• Fast Cloud Storage\n"
        "• Direct Streaming Links\n"
        "• Create your own Clone Bot"
    )

    # Main Menu Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))
        ],
        [
            InlineKeyboardButton("📂 My Files", callback_data="my_files"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [
            InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ]
    ])

    await message.reply_text(text, reply_markup=buttons, quote=True)


# --- CALLBACK HANDLERS ---

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_callback(client, callback_query):
    await callback_query.answer()
    
    # Import CLONE_SESSION dynamically to avoid circular imports with commands.py
    try:
        from bot.plugins.commands import CLONE_SESSION
        
        # Set the user state to 'WAIT_TOKEN' immediately
        user_id = callback_query.from_user.id
        CLONE_SESSION[user_id] = {"step": "WAIT_TOKEN"}
        
        await callback_query.message.edit_text(
            "🤖 **Clone Bot Creation Wizard**\n\n"
            "1. Go to @BotFather and create a new bot.\n"
            "2. Copy the **API Token**.\n"
            "3. **Send the Token here.**\n\n"
            "_(Send /cancel to stop)_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
        )
    except ImportError:
        await callback_query.message.edit_text(
            "⚠️ Error initializing wizard. Please use the `/clone` command instead.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
        )

@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user = await users_col.find_one({"user_id": user_id})
    
    # Default is False (OFF)
    is_short = user.get("use_short", False) if user else False
    
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

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    # Go back to the main start message
    await start_handler(client, callback_query.message)
    # If start_handler sent a new message (due to reply), delete the old one to keep chat clean
    # However, start_handler usually replies to a command. 
    # Here we are editing. So we can just call the function logic or recreate the message.
    # To keep it simple, we delete the callback message and send a fresh start.
    await callback_query.message.delete()

@Client.on_callback_query(filters.regex("help"))
async def help_callback(client, callback_query):
    await callback_query.message.edit_text(
        "❓ **Help Guide**\n\n"
        "1. **Upload File:** Send any file to the bot.\n"
        "2. **Get Link:** The bot will reply with a stream link.\n"
        "3. **Dashboard:** Click 'My Dashboard' to manage files.\n"
        "4. **Clone:** Click 'Create Your Own Bot' to start the wizard.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("about"))
async def about_callback(client, callback_query):
    await callback_query.message.edit_text(
        "ℹ️ **About This Bot**\n\n"
        "This bot is a powerful File Store & Link Generator.\n"
        "It features a Web App Dashboard, Clone functionality, and persistent storage.\n\n"
        "Developed with ❤️ using Python & Pyrogram.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("my_files"))
async def my_files_callback(client, callback_query):
    # Just a placeholder or simple text since the main UI is the Web App
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    await callback_query.answer("Open the Dashboard to view files!", show_alert=True)
    # Optional: You could actually list files here via pagination, but Web App is better.
