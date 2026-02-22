import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.clone import db, clones_col
from config import Config
from bot_client import tg_bot # Import Main Bot instance to get its username

# Database Collections
users_col = db.users
auth_codes_col = db.auth_codes

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 0. HANDLE DEEP LINKS (Redirects & Login) ---
    if len(message.command) > 1:
        payload = message.command[1]
        
        # A. Login Verification
        if payload.startswith("login_"):
            token = payload.replace("login_", "")
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
        
        # B. Create Bot Redirect (Trigger Wizard)
        elif payload == "create_bot":
            # Simulate clicking the "Create Bot" button
            # We create a dummy callback query to reuse the existing function
            class MockCallback:
                def __init__(self, msg, usr):
                    self.message = msg
                    self.from_user = usr
                async def answer(self, *args, **kwargs): pass
            
            mock_cb = MockCallback(message, message.from_user)
            await clone_info_callback(client, mock_cb)
            return

    # --- 1. SAVE USER TO DB ---
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except Exception:
        pass

    # --- 2. DETERMINE IF MAIN BOT OR CLONE ---
    # We compare the current client's ID with the Main Bot's ID (from Config Token)
    main_bot_id = int(Config.BOT_TOKEN.split(":")[0])
    is_main_bot = (client.me.id == main_bot_id)

    # --- 3. CONSTRUCT BUTTONS ---
    
    # Clone Button Logic
    if is_main_bot:
        # If Main Bot: Check DB for existing clone
        user_clone = await clones_col.find_one({"user_id": message.from_user.id})
        if user_clone:
            clone_btn = InlineKeyboardButton("🤖 Manage Your Bot", callback_data="manage_clone")
        else:
            clone_btn = InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")
    else:
        # If Clone Bot: Redirect to Main Bot
        # We need Main Bot Username. Since tg_bot is the main client, we use that.
        main_username = tg_bot.me.username if tg_bot.me else "red_b_bot" # Fallback if not cached yet
        clone_btn = InlineKeyboardButton("🤖 Create Your Own Bot", url=f"https://t.me/{main_username}?start=create_bot")

    # Web App URL
    base_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    bot_id = client.me.id
    sep = "&" if "?" in base_url else "?"
    web_app_url = f"{base_url}{sep}bot_id={bot_id}"

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

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=web_app_url))
        ],
        [
            InlineKeyboardButton("📂 My Files", callback_data="my_files"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ],
        [
            clone_btn # Dynamically decided above
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ]
    ])

    await message.reply_text(text, reply_markup=buttons, quote=True)


# --- CALLBACK HANDLERS ---

@Client.on_callback_query(filters.regex("manage_clone"))
async def manage_clone_callback(client, callback_query):
    user_clone = await clones_col.find_one({"user_id": callback_query.from_user.id})
    
    if not user_clone:
        await callback_query.answer("Clone not found!", show_alert=True)
        return

    text = (
        f"🤖 **Your Clone Bot Details**\n\n"
        f"👤 **Bot Username:** @{user_clone.get('username', 'Unknown')}\n"
        f"📢 **Connected Channel:** `{user_clone.get('log_channel', 'Unknown')}`\n\n"
        "⚠️ **To Delete or Re-make:**\n"
        "Use the **Dashboard** settings or simply create a new one using `/clone` command (it will overwrite this one)."
    )
    
    # If the user clicks this on a Clone Bot (edge case), we still show the info, 
    # but they can't effectively manage it except via Main Bot or Dashboard.
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    )

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_callback(client, callback_query):
    # This might be called via the mock object in start_handler, so we check if it has .answer
    if hasattr(callback_query, "answer"):
        await callback_query.answer()
    
    try:
        from bot.plugins.commands import CLONE_SESSION
        
        # Start Wizard State
        user_id = callback_query.from_user.id
        CLONE_SESSION[user_id] = {"step": "WAIT_TOKEN"}
        
        msg = callback_query.message
        
        # If it was a callback (edit message)
        if hasattr(msg, "edit_text"):
            await msg.edit_text(
                "🤖 **Clone Bot Creation Wizard**\n\n"
                "1. Go to @BotFather and create a new bot.\n"
                "2. Copy the **API Token**.\n"
                "3. **Send the Token here.**\n\n"
                "_(Send /cancel to stop)_",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
            )
        # If it was a redirect (reply new message)
        else:
             await msg.reply_text(
                "🤖 **Clone Bot Creation Wizard**\n\n"
                "1. Go to @BotFather and create a new bot.\n"
                "2. Copy the **API Token**.\n"
                "3. **Send the Token here.**\n\n"
                "_(Send /cancel to stop)_"
            )

    except ImportError:
        if hasattr(callback_query.message, "edit_text"):
            await callback_query.message.edit_text("⚠️ Error initializing wizard. Use `/clone`.")

@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user = await users_col.find_one({"user_id": user_id})
    is_short = user.get("use_short", False) if user else False
    status_text = "✅ ON" if is_short else "❌ OFF"
    toggle_data = "false" if is_short else "true"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔗 Short Link (TinyURL): {status_text}", callback_data=f"toggle_short_{toggle_data}")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text("⚙️ **User Settings**", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^toggle_short_"))
async def toggle_short_handler(client, callback_query):
    new_status = callback_query.data.split("_")[2] == "true"
    await users_col.update_one({"user_id": callback_query.from_user.id}, {"$set": {"use_short": new_status}}, upsert=True)
    await settings_callback(client, callback_query)

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    await start_handler(client, callback_query.message)
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
    await callback_query.answer("Open the Dashboard to view files!", show_alert=True)
