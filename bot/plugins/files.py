import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, WebAppInfo
from config import Config
from bot.utils import is_subscribed, get_tinyurl
from bot.clone import db

files_col = db.files
users_col = db.users
BATCH_DATA = {}

# --- HELPER: Human Readable Size ---
def humanbytes(b):
    if not b: return ""
    for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
        if b < 1024: return f"{b:.2f}{unit}B"
        b /= 1024
    return f"{b:.2f}PiB"

# --- HELPER: Generate Buttons ---
def get_file_buttons(msg_id, link, is_protected=False):
    protect_text = "📝 Edit Password" if is_protected else "🔒 Protect"
    return InlineKeyboardMarkup([
        [
            # Open in Web App (Mini App) for streaming
            InlineKeyboardButton("📺 Watch / Stream", web_app=WebAppInfo(url=link)),
            InlineKeyboardButton("🚀 Fast Download", url=link)
        ],
        [
            InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{msg_id}"),
            InlineKeyboardButton(protect_text, callback_data=f"protect_{msg_id}")
        ],
        [
            InlineKeyboardButton("⏳ Set Validity", callback_data=f"validity_{msg_id}")
        ]
    ])

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    # 1. Check Force Subscribe (Skip for Owner/Admins if needed, but keeping simple)
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **You must join our channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_URL)],
                [InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start=start")]
            ])
        )

    # 2. DETERMINE TARGET LOG CHANNEL
    # If client has 'log_channel' set (Clone), use it. Otherwise use Config (Main Bot).
    log_channel = getattr(client, "log_channel", None) or Config.LOG_CHANNEL_ID

    if not log_channel:
        # If it's a clone but hasn't connected a DB yet
        if getattr(client, "owner_id", None):
             await message.reply("❌ **Database Not Connected.**\nUse `/connect` in your Log Channel first.")
        else:
             await message.reply("❌ **System Error:** Main Bot Log Channel not set in Config.")
        return

    # 3. Handle Media Groups (Batch)
    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in BATCH_DATA:
            BATCH_DATA[mg_id] = []
            asyncio.create_task(process_batch(client, mg_id, message.chat.id, message.from_user.id, log_channel))
        BATCH_DATA[mg_id].append(message)
        return

    # 4. Process Single File
    await process_file(client, message, log_channel)

async def process_batch(client, mg_id, chat_id, user_id, log_channel):
    await asyncio.sleep(4)
    messages = BATCH_DATA.pop(mg_id, [])
    
    user = await users_col.find_one({"user_id": user_id})
    use_short = user.get("use_short", False) if user else False

    links_text = "**📦 Batch Links:**\n\n"
    for msg in messages:
        try:
            log_msg = await msg.copy(chat_id=log_channel)
        except Exception as e:
            continue # Skip files that fail to copy (permissions?)

        media = msg.document or msg.video or msg.audio
        await save_file_to_db(msg, log_msg, media, log_channel)
        
        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
        final_link = await get_tinyurl(base_link) if use_short else base_link
        
        links_text += f"• [{getattr(media, 'file_name', 'File')}]({final_link})\n"
    
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message, log_channel):
    try:
        # Copy to the determined Log Channel
        log_msg = await message.copy(chat_id=log_channel)
        media = message.document or message.video or message.audio
        
        await save_file_to_db(message, log_msg, media, log_channel)

        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        user = await users_col.find_one({"user_id": message.from_user.id})
        use_short = user.get("use_short", False) if user else False

        final_link = await get_tinyurl(base_link) if use_short else base_link
        
        file_name = getattr(media, "file_name", "file")
        file_size = getattr(media, "file_size", 0)

        caption = (
            f"✅ **Link Generated!**\n\n"
            f"📂 **Name:** `{file_name}`\n\n"
            f"📦 **Size:** {humanbytes(file_size)}\n\n"
            f"🔗 **Download Link:**\n`{final_link}`"
        )
        
        await message.reply_text(
            caption,
            reply_markup=get_file_buttons(log_msg.id, final_link, is_protected=False),
            quote=True
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** {e}\n\nMake sure I am an **Admin** in your Log Channel.")

async def save_file_to_db(user_msg, log_msg, media, channel_id):
    await files_col.insert_one({
        "user_id": user_msg.from_user.id,
        "log_msg_id": log_msg.id,
        "channel_id": channel_id, # <--- Stores which channel the file is in
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "file_unique_id": media.file_unique_id,
        "timestamp": user_msg.date,
        "password": None,
        "expiry": None
    })

# --- CALLBACK HANDLERS (Rename, Protect, Validity) ---
# ... (These remain largely the same, just ensure imports match) ...

@Client.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await client.send_message(
        callback_query.message.chat.id,
        "📝 **Enter new file name:**",
        reply_markup=ForceReply(selective=True, placeholder=f"rename_{file_id}")
    )

@Client.on_callback_query(filters.regex(r"^protect_"))
async def protect_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await client.send_message(
        callback_query.message.chat.id,
        "🔒 **Enter password for this link:**",
        reply_markup=ForceReply(selective=True, placeholder=f"protect_{file_id}")
    )
    await callback_query.message.delete()

@Client.on_callback_query(filters.regex(r"^validity_"))
async def validity_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("30 Mins", callback_data=f"settime_{file_id}_30m"), InlineKeyboardButton("1 Hour", callback_data=f"settime_{file_id}_1h")],
        [InlineKeyboardButton("1 Day", callback_data=f"settime_{file_id}_1d"), InlineKeyboardButton("1 Week", callback_data=f"settime_{file_id}_7d")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"back_{file_id}")]
    ])
    await callback_query.message.edit_text("⏳ **Select Link Validity:**", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^back_"))
async def back_to_main_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await send_updated_message(client, callback_query.message.chat.id, file_id, message_to_edit=callback_query.message)

@Client.on_callback_query(filters.regex(r"^settime_"))
async def set_validity_handler(client, callback_query):
    _, file_id, duration = callback_query.data.split("_")
    seconds = 0
    if duration == "30m": seconds = 1800
    elif duration == "1h": seconds = 3600
    elif duration == "1d": seconds = 86400
    elif duration == "7d": seconds = 604800
    
    expiry_time = time.time() + seconds
    await files_col.update_one({"log_msg_id": int(file_id)}, {"$set": {"expiry": expiry_time}})
    await callback_query.answer("✅ Validity Set!", show_alert=True)
    await send_updated_message(client, callback_query.message.chat.id, int(file_id), message_to_edit=callback_query.message)

@Client.on_callback_query(filters.regex("close"))
async def close_cb(client, callback_query):
    await callback_query.message.delete()

@Client.on_message(filters.private & filters.reply)
async def input_handler(client, message):
    reply = message.reply_to_message
    if not reply or not reply.reply_markup or not isinstance(reply.reply_markup, ForceReply):
        return

    placeholder = reply.reply_markup.placeholder
    if not placeholder or "_" not in placeholder: return
    
    action, file_id = placeholder.split("_")
    file_id = int(file_id)
    
    file_data = await files_col.find_one({"log_msg_id": file_id})
    if not file_data:
        return await message.reply("❌ File not found in DB.")

    if action == "rename":
        await files_col.update_one({"_id": file_data["_id"]}, {"$set": {"file_name": message.text}})
        await message.reply(f"✅ **Renamed to:** `{message.text}`")
    elif action == "protect":
        await files_col.update_one({"_id": file_data["_id"]}, {"$set": {"password": message.text}})
    
    try:
        await message.delete()
        await reply.delete()
    except: pass

    await send_updated_message(client, message.chat.id, file_id)

async def send_updated_message(client, chat_id, file_id, message_to_edit=None):
    file_data = await files_col.find_one({"log_msg_id": file_id})
    if not file_data: return

    base_link = f"{Config.BLOGGER_URL}?id={file_id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{file_id}"
    
    user_id = file_data.get("user_id")
    user = await users_col.find_one({"user_id": user_id})
    use_short = user.get("use_short", False) if user else False
    final_link = await get_tinyurl(base_link) if use_short else base_link
    
    is_protected = bool(file_data.get("password"))
    pass_text = f"\n\n🔐 **Password:** `{file_data.get('password')}`" if is_protected else ""
    
    validity_text = ""
    if file_data.get("expiry"):
        remaining = int(file_data['expiry'] - time.time())
        validity_text = f"\n\n⏳ **Expires in:** {remaining//60} mins" if remaining > 0 else "\n\n🚫 **Link Expired**"

    caption = (
        f"✅ **File Settings Updated!**\n\n"
        f"📂 **Name:** `{file_data['file_name']}`\n\n"
        f"📦 **Size:** {humanbytes(file_data['file_size'])}"
        f"{pass_text}"
        f"{validity_text}\n\n"
        f"🔗 **Link:**\n`{final_link}`"
    )

    markup = get_file_buttons(file_id, final_link, is_protected)

    if message_to_edit:
        await message_to_edit.edit_text(caption, reply_markup=markup)
    else:
        await client.send_message(chat_id, caption, reply_markup=markup)
