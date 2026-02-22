import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.clone import db
from config import Config
from bot_client import tg_bot

async def get_main_menu(client, user_id, first_name):
    # Determine Main Bot
    main_bot_id = int(Config.BOT_TOKEN.split(":")[0])
    if not client.me: await client.get_me()
    is_main_bot = (client.me.id == main_bot_id)

    # Clone Logic
    if is_main_bot:
        # DB ACCESS INSIDE FUNCTION -> SAFE
        user_clone = await db.clones.find_one({"user_id": user_id})
        if user_clone: clone_btn = InlineKeyboardButton("🤖 Manage Your Bot", callback_data="manage_clone")
        else: clone_btn = InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_info")
    else:
        main_username = tg_bot.me.username if tg_bot.me else "red_b_bot"
        clone_btn = InlineKeyboardButton("🤖 Create Your Own Bot", url=f"https://t.me/{main_username}?start=create_bot")

    # Web App
    base_url = Config.BLOGGER_URL if Config.BLOGGER_URL else Config.BASE_URL
    bot_id = client.me.id
    sep = "&" if "?" in base_url else "?"
    dashboard_url = f"{base_url}{sep}bot_id={bot_id}"
    files_url = f"{base_url}{sep}bot_id={bot_id}&tab=files"

    text = f"👋 **Hi {first_name}!**\n\nI am a **File Store Bot**.\nSend files to get a link."
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 My Dashboard", web_app=WebAppInfo(url=dashboard_url))],
        [InlineKeyboardButton("📂 My Files", web_app=WebAppInfo(url=files_url)), InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [clone_btn],
        [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])
    return text, buttons

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if len(message.command) > 1:
        payload = message.command[1]
        
        if payload.startswith("login_"):
            token = payload.replace("login_", "")
            # DB ACCESS INSIDE FUNCTION -> SAFE
            result = await db.auth_codes.update_one(
                {"token": token, "status": "pending"},
                {"$set": {
                    "status": "verified",
                    "user_id": message.from_user.id,
                    "user_info": {"id": message.from_user.id, "first_name": message.from_user.first_name},
                    "role": "admin" if message.from_user.id in Config.ADMIN_IDS else "user"
                }}
            )
            if result.modified_count > 0: await message.reply("✅ **Login Successful!**", quote=True)
            else: await message.reply("❌ **Link Expired.**", quote=True)
            return
            
        elif payload == "create_bot":
            try:
                from bot.plugins.commands import CLONE_SESSION
                CLONE_SESSION[message.from_user.id] = {"step": "WAIT_TOKEN"}
                await message.reply_text("🤖 **Clone Bot Wizard**\nSend Token.", reply_markup=ForceReply(selective=True, placeholder="Token..."))
            except: pass
            return

    try: 
        # DB ACCESS INSIDE FUNCTION -> SAFE
        await db.users.update_one({"user_id": message.from_user.id}, {"$set": {"user_id": message.from_user.id}}, upsert=True)
    except: pass

    text, buttons = await get_main_menu(client, message.from_user.id, message.from_user.first_name)
    await message.reply_text(text, reply_markup=buttons, quote=True)

@Client.on_callback_query(filters.regex("start_menu"))
async def back_to_start(client, callback_query):
    text, buttons = await get_main_menu(client, callback_query.from_user.id, callback_query.from_user.first_name)
    await callback_query.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("manage_clone"))
async def manage_clone_callback(client, callback_query):
    # DB ACCESS INSIDE FUNCTION -> SAFE
    user_clone = await db.clones.find_one({"user_id": callback_query.from_user.id})
    if not user_clone: return await callback_query.answer("Clone not found!", show_alert=True)
    await callback_query.message.edit_text(f"🤖 **Clone Bot**\n@{user_clone.get('username')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]))

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_info_callback(client, callback_query):
    try:
        from bot.plugins.commands import CLONE_SESSION
        CLONE_SESSION[callback_query.from_user.id] = {"step": "WAIT_TOKEN"}
        await callback_query.message.edit_text("🤖 **Clone Bot Wizard**\nSend Token.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]))
    except: pass

@Client.on_callback_query(filters.regex("settings"))
async def settings_callback(client, callback_query):
    # DB ACCESS INSIDE FUNCTION -> SAFE
    user = await db.users.find_one({"user_id": callback_query.from_user.id})
    is_short = user.get("use_short", False) if user else False
    status_text = "✅ ON" if is_short else "❌ OFF"
    toggle_data = "false" if is_short else "true"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton(f"🔗 Short Link: {status_text}", callback_data=f"toggle_short_{toggle_data}")], [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]])
    await callback_query.message.edit_text("⚙️ **Settings**", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^toggle_short_"))
async def toggle_short_handler(client, callback_query):
    new_status = callback_query.data.split("_")[2] == "true"
    await db.users.update_one({"user_id": callback_query.from_user.id}, {"$set": {"use_short": new_status}}, upsert=True)
    await settings_callback(client, callback_query)

@Client.on_callback_query(filters.regex("help"))
async def help_callback(client, callback_query):
    await callback_query.message.edit_text("❓ **Help**\nSend a file to get a link.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]))

@Client.on_callback_query(filters.regex("about"))
async def about_callback(client, callback_query):
    await callback_query.message.edit_text("ℹ️ **About**\nFile Store Bot.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start_menu")]]))

@Client.on_callback_query(filters.regex("my_files"))
async def my_files_callback(client, callback_query):
    await callback_query.answer("Open the Dashboard!", show_alert=True)
