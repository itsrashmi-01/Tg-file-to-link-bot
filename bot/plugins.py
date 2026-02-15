from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from bot.fsub import get_fsub_status
from bot.clone import start_clone_bot, clones_col, RUNNING_CLONES
from bot.tinyurl_helper import shorten_url
import secrets
import datetime

# --- Database Setup ---
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
files_col = db.large_files
users_col = db.large_file_users

# --- State Management ---
user_states = {}
temp_tokens = {}

# --- Default Bot Image ---
DEFAULT_PIC = getattr(Config, 'BOT_PIC', "https://i.imgur.com/8Qj8X9L.jpeg")

# ==================================================================
# 1. START COMMAND & MAIN MENU
# ==================================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if not await get_fsub_status(client, message): return

    # Clear conversation state
    if message.from_user.id in user_states: del user_states[message.from_user.id]

    # Initialize User Data (Default Shortener: OFF)
    await users_col.update_one(
        {"_id": message.from_user.id},
        {"$setOnInsert": {"shortener_active": False}}, 
        upsert=True
    )
    # Update Last Active
    await users_col.update_one(
        {"_id": message.from_user.id},
        {"$set": {
            "first_name": message.from_user.first_name, 
            "username": message.from_user.username, 
            "last_active": datetime.datetime.now()
        }}
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 My Links", callback_data="my_links"), InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("🤖 Create Your Own Bot", callback_data="clone_start")],
        [InlineKeyboardButton("🔗 Shortener Settings", callback_data="shortener_menu")], 
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"), InlineKeyboardButton("👨‍💻 About", callback_data="about")]
    ])

    await message.reply_photo(
        photo=DEFAULT_PIC, 
        caption=f"👋 **Hello {message.from_user.first_name}!**\n\nI am your **Advanced File Manager Bot**.\nI can store files up to **4GB**.", 
        reply_markup=buttons
    )

# ==================================================================
# 2. SHORTENER SETTINGS
# ==================================================================
@Client.on_callback_query(filters.regex("shortener_menu"))
async def shortener_menu_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    user = await users_col.find_one({"_id": user_id})
    
    is_active = user.get("shortener_active", False)
    status_text = "🟢 **ON**" if is_active else "🔴 **OFF**"
    toggle_cb = "shortener_off" if is_active else "shortener_on"

    text = (
        f"🔗 **URL Shortener Settings**\n\n"
        f"**Status:** {status_text}\n"
        f"**Provider:** TinyURL (Unlimited)\n\n"
        f"When ON, all your file links will be automatically shortened."
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Turn {('OFF' if is_active else 'ON')}", callback_data=toggle_cb)],
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])
    await query.message.edit_caption(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("shortener_(on|off)"))
async def shortener_toggle_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    new_status = True if query.data == "shortener_on" else False
    
    await users_col.update_one({"_id": user_id}, {"$set": {"shortener_active": new_status}})
    await shortener_menu_handler(client, query) # Refresh Menu

# ==================================================================
# 3. CLONE CONVERSATION (USER PROVIDES CHANNEL)
# ==================================================================
@Client.on_message(filters.command("clone") & filters.private)
async def clone_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_states[user_id] = "WAITING_FOR_TOKEN"
    await message.reply_text("🤖 **Create Your Own Bot**\n\nSend your **Bot Token** from @BotFather.\n*(Send /cancel to stop)*")

@Client.on_callback_query(filters.regex("clone_start"))
async def clone_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    user_states[user_id] = "WAITING_FOR_TOKEN"
    await query.message.reply_text("🤖 **Create Your Own Bot**\n\nSend your **Bot Token** from @BotFather.\n*(Send /cancel to stop)*")
    await query.answer()

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "clone"]))
async def conversation_handler(client: Client, message: Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if message.text == "/cancel":
        if user_id in user_states: del user_states[user_id]
        if user_id in temp_tokens: del temp_tokens[user_id]
        await message.reply_text("❌ **Process Cancelled.**")
        return

    # --- HANDLE TOKEN INPUT ---
    if state == "WAITING_FOR_TOKEN":
        token = message.text.strip()
        if ":" not in token or len(token) < 20:
            await message.reply_text("❌ **Invalid Token.** Check @BotFather.")
            return

        temp_tokens[user_id] = token
        user_states[user_id] = "WAITING_FOR_CHANNEL"
        
        await message.reply_text(
            "✅ **Token Received!**\n\n"
            "Now, send the **Channel ID** (e.g., `-100xxxx`) OR **Link** (`https://t.me/xxxx`).\n\n"
            "⚠️ **IMPORTANT:** Add your new bot as **Admin** in this channel FIRST!"
        )
        return

    # --- HANDLE CHANNEL INPUT ---
    elif state == "WAITING_FOR_CHANNEL":
        raw_input = message.text.strip()
        channel_input = None

        # 1. Check if it's a numeric ID
        if raw_input.lstrip("-").isdigit():
            channel_input = int(raw_input)
        
        # 2. Check if it's a Link (t.me/username)
        elif "t.me/" in raw_input or "telegram.me/" in raw_input:
            parts = raw_input.split("/")
            # Get the last part (username)
            last_part = parts[-1].split("?")[0] # Remove query params
            
            if "+" in last_part or "joinchat" in parts:
                await message.reply_text("❌ **Error:** Private Invite Links (with `+`) are not supported.\nPlease use a **Public Channel Link** or the **Channel ID**.")
                return
            
            channel_input = f"@{last_part}"
            
        # 3. Check if it's a Username (@username)
        elif raw_input.startswith("@"):
            channel_input = raw_input
            
        else:
            # Assume it's a username without @
            channel_input = f"@{raw_input}"

        # START CLONING
        token = temp_tokens.get(user_id)
        status_msg = await message.reply_text("♻️ **Connecting to Channel...**")
        
        # Pass the user input (ID or Username) to the clone starter
        bot_info, final_id = await start_clone_bot(token, channel_input)

        if not bot_info:
            await status_msg.edit(
                "❌ **Connection Failed.**\n\n"
                "1. Is the Bot Token correct?\n"
                "2. Is the Bot an **Admin** in that channel?\n"
                "3. If using a link, is the channel **Public**?"
            )
        else:
            # Save to DB
            await clones_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "token": token,
                    "log_channel": final_id, # User's own channel
                    "bot_id": bot_info.id,
                    "username": bot_info.username,
                    "name": bot_info.first_name
                }},
                upsert=True
            )
            
            # Notify Admin (Global Log)
            try:
                await client.send_message(
                    int(Config.LOG_CHANNEL),
                    f"🤖 **New Clone Created!**\n@{bot_info.username}\nChannel: {final_id}"
                )
            except: pass

            await status_msg.edit(
                f"✅ **Clone Successful!**\n\n"
                f"🤖 **Bot:** @{bot_info.username}\n"
                f"📢 **Channel:** `{final_id}`"
            )

        # Cleanup
        del user_states[user_id]
        del temp_tokens[user_id]

# ==================================================================
# 4. CALLBACK HANDLERS (Profile, Links, Help)
# ==================================================================
@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    if data == "clone_start": pass 
    elif data == "my_profile":
        user = await users_col.find_one({"_id": user_id})
        count = await files_col.count_documents({"user_id": user_id})
        await query.message.edit_caption(f"👤 **Profile**\n🆔 `{user_id}`\n📂 Files: {count}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))
    elif data == "my_links":
        count = await files_col.count_documents({"user_id": user_id})
        await query.answer(f"📂 Saved Files: {count}", show_alert=True)
    elif data == "help":
        await query.message.edit_caption("ℹ️ **Help**\n\n1. Send File -> Get Link.\n2. /clone -> Create Bot.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))
    elif data == "about":
        text = "<b>About</b>\n\n🤖 File Stream Bot\n📚 Pyrogram"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🧑🏻‍💻 Developer", url="https://t.me/YourUsername"), InlineKeyboardButton("🔙 Back", callback_data="home")]])
        await query.message.edit_caption(text, reply_markup=buttons)
    elif data == "home":
        await query.message.delete()
        await start_handler(client, query.message)

# ==================================================================
# 5. FILE HANDLER (Auto-Forward + Shortener)
# ==================================================================
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_large_file(client: Client, message: Message):
    if user_states.get(message.from_user.id): return
    if not await get_fsub_status(client, message): return

    # --- INTELLIGENT ROUTING ---
    # Determine which channel to use (Main or Clone's private channel)
    clone_data = RUNNING_CLONES.get(client.me.id)
    target_channel = clone_data['log_channel'] if clone_data else int(Config.LOG_CHANNEL)

    try:
        log_msg = await message.forward(target_channel)
    except Exception as e:
        if "Peer id invalid" in str(e):
             await message.reply_text(f"❌ **Error:** I cannot see channel `{target_channel}`. Please send a message in that channel to wake me up.")
        else:
             await message.reply_text(f"❌ **Error:** Cannot forward to Log Channel (`{target_channel}`).\nMake sure I am an **Admin** there.")
        return

    unique_id = secrets.token_urlsafe(8)
    media = message.document or message.video or message.audio
    file_name = getattr(media, 'file_name', 'video.mp4')
    mime_type = getattr(media, 'mime_type', 'video/mp4')
    file_size = getattr(media, 'file_size', 0)

    await files_col.insert_one({
        "unique_id": unique_id, "user_id": message.from_user.id, "message_id": log_msg.id, 
        "file_name": file_name, "mime_type": mime_type, "file_size": file_size, "created_at": datetime.datetime.now()
    })
    
    # Generate Link
    base_url = Config.BLOGGER_URL if Config.BLOGGER_URL else f"{Config.URL}/watch"
    link = f"{base_url}?id={unique_id}" if Config.BLOGGER_URL else f"{base_url}/{unique_id}"
    
    # --- SHORTENER CHECK ---
    user = await users_col.find_one({"_id": message.from_user.id})
    if user and user.get("shortener_active"):
        status_msg = await message.reply_text("⏳ **Shortening...**")
        short_link = await shorten_url(link)
        if short_link:
            link = short_link
            await status_msg.delete()
        else:
            await status_msg.edit("⚠️ Shortener failed, sending normal link.")

    await message.reply_text(
        f"✅ **File Secured!**\n\n"
        f"📂 `{file_name}`\n"
        f"💾 `{round(file_size / 1024 / 1024, 2)} MB`\n\n"
        f"🔗 **Link:** {link}", 
        disable_web_page_preview=True
    )
