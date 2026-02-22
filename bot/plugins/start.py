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

    # URL for the Mini App
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    update_channel_url = Config.FORCE_SUB_URL if Config.FORCE_SUB_URL else "https://t.me/telegram"

    # Welcome Text
    text = (
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "I am a **File Store & Link Generator Bot**.\n"
        "Send me any file (Video, Audio, Document), and I will generate a direct download and streaming link for you.\n\n"
        "🚀 **Features:**\n"
        "• Fast Cloud Storage\n"
        "• Direct Streaming Links\n"
        "• File Management Dashboard\n\n"
        "Click the buttons below to explore!"
    )

    # Buttons
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
            InlineKeyboardButton("📢 Update Channel", url=update_channel_url),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ])

    await message.reply_text(
        text=text,
        reply_markup=buttons,
        quote=True,
        disable_web_page_preview=True
    )

# --- CALLBACK HANDLERS FOR NEW BUTTONS ---
# You can expand these functions to add logic for the buttons

@Client.on_callback_query(filters.regex("about"))
async def about_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "ℹ️ **About This Bot**\n\n"
        "This bot helps you convert Telegram files into direct HTTP links.\n"
        "It features a Web App Dashboard for easy file management.\n\n"
        "Developed with ❤️ using Python & Pyrogram.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("help"))
async def help_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "❓ **Help Guide**\n\n"
        "1. **Upload File:** Send any file to the bot.\n"
        "2. **Get Link:** The bot will reply with a stream link.\n"
        "3. **Dashboard:** Click 'My Dashboard' to manage files.\n"
        "4. **Clone:** Use `/clone` to create your own instance.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_callback(client, callback_query):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "🤖 **Create Your Own Bot**\n\n"
        "You can clone this bot functionality using your own Bot Token.\n\n"
        "**Command:** `/clone <your_bot_token>`\n\n"
        "Get a token from @BotFather and send the command here.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    # Re-sends the start menu (Copy logic from start_handler text/buttons)
    web_app_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    update_channel_url = Config.FORCE_SUB_URL if Config.FORCE_SUB_URL else "https://t.me/telegram"
    
    text = (
        f"👋 **Welcome Back!**\n\n"
        "I am your File Store & Link Generator Bot.\n"
        "Select an option below:"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("📂 My Files", callback_data="my_files"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")],
        [InlineKeyboardButton("📢 Update Channel", url=update_channel_url), InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])
    
    await callback_query.message.edit_text(
        text=text,
        reply_markup=buttons
    )
