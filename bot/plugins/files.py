import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from config import Config
from bot.utils import is_subscribed, get_tinyurl
from bot.clone import db

files_col = db.files
users_col = db.users
BATCH_DATA = {}

# --- HELPER: Human Readable Size ---
def humanbytes(b):
    if not b: return "0 B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
        if b < 1024: return f"{b:.2f} {unit}B"
        b /= 1024
    return f"{b:.2f} PiB"

# --- HELPER: Generate Buttons ---
def get_file_buttons(msg_id, link, user_id, is_protected=False):
    protect_text = "📝 Edit Password" if is_protected else "🔒 Protect"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Open Link", url=link),
            InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={link}&text=Check+this+file!")
        ],
        [
            InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{msg_id}"),
            InlineKeyboardButton(protect_text, callback_data=f"protect_{msg_id}")
        ],
        [
            InlineKeyboardButton("⏳ Set Validity", callback_data=f"validity_{msg_id}"),
            InlineKeyboardButton("🗑️ Close", callback_data="close")
        ]
    ])

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    # Force Subscribe Check
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nYou must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_URL)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start=start")]
            ])
        )

    # Handle Albums/Media Groups
    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in BATCH_DATA:
            BATCH_DATA[mg_id] = []
            asyncio.create_task(process_batch(client, mg_id, message.chat.id, message.from_user.id))
        BATCH_DATA[mg_id].append(message)
        return

    await process_file(client, message)

async def process_batch(client, mg_id, chat_id, user_id):
    await asyncio.sleep(4)
    messages = BATCH_DATA.pop(mg_id, [])
    
    # Identify Correct Log Channel (Dynamic for Clones)
    log_channel = getattr(client, "log_channel", Config.LOG_CHANNEL_ID)
    
    user = await users_col.find_one({"user_id": user_id})
    use_short = user.get("use_short", False) if user else False

    links_text = "📦 **Batch Processed Successfully!**\n\n"
    for msg in messages:
        media = msg.document or msg.video or msg.audio
        log_msg = await msg.copy(chat_id=log_channel)
        
        await save_file_to_db(user_id, log_msg, media, log_channel)
        
        # Link includes user_id so the server knows which bot client to use
        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}&user_id={user_id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}?user_id={user_id}"
        final_link = await get_tinyurl(base_link) if use_short else base_link
        
        links_text += f"• `{getattr(media, 'file_name', 'File')}`\n🔗 {final_link}\n\n"
    
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message):
    try:
        user_id = message.from_user.id
        # Dynamic Channel Selection
        log_channel = getattr(client, "log_channel", Config.LOG_CHANNEL_ID)
        
        media = message.document or message.video or message.audio
        log_msg = await message.copy(chat_id=log_channel)
        
        await save_file_to_db(user_id, log_msg, media, log_channel)

        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}&user_id={user_id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}?user_id={user_id}"
        
        user = await users_col.find_one({"user_id": user_id})
        use_short = user.get("use_short", False) if user else False
        final_link = await get_tinyurl(base_link) if use_short else base_link
        
        file_name = getattr(media, "file_name", "file")
        file_size = getattr(media, "file_size", 0)

        caption = (
            f"✅ **Link Generated!**\n\n"
            f"📂 **Name:** `{file_name}`\n"
            f"📦 **Size:** `{humanbytes(file_size)}`\n\n"
            f"🔗 **Direct Link:**\n`{final_link}`"
        )
        
        await message.reply_text(
            caption,
            reply_markup=get_file_buttons(log_msg.id, final_link, user_id),
            quote=True
        )

    except Exception as e:
        await message.reply_text(f"❌ **Error:** {e}")

async def save_file_to_db(user_id, log_msg, media, log_channel):
    # Unified 'expire_at' field for the cleaner task in main.py
    await files_col.insert_one({
        "user_id": user_id,
        "log_msg_id": log_msg.id,
        "log_channel": log_channel,
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "file_unique_id": media.file_unique_id,
        "timestamp": time.time(),
        "password": None,
        "expire_at": None 
    })

# --- CALLBACKS & UPDATES ---

async def send_updated_message(client, chat_id, log_msg_id, message_to_edit=None):
    file_data = await files_col.find_one({"log_msg_id": log_msg_id})
    if not file_data: return

    user_id = file_data['user_id']
    base_link = f"{Config.BLOGGER_URL}?id={log_msg_id}&user_id={user_id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg_id}?user_id={user_id}"
    
    user = await users_col.find_one({"user_id": user_id})
    final_link = await get_tinyurl(base_link) if (user and user.get("use_short")) else base_link
    
    is_protected = bool(file_data.get("password"))
    pass_text = f"\n🔐 **Password:** `{file_data.get('password')}`" if is_protected else ""
    
    validity_text = ""
    if file_data.get("expire_at"):
        rem = int(file_data['expire_at'] - time.time())
        validity_text = f"\n⏳ **Expires in:** {rem//3600}h {(rem%3600)//60}m" if rem > 0 else "\n🚫 **Expired**"

    caption = (
        f"⚙️ **File Settings Updated**\n\n"
        f"📂 **Name:** `{file_data['file_name']}`\n"
        f"📦 **Size:** `{humanbytes(file_data['file_size'])}`"
        f"{pass_text}{validity_text}\n\n"
        f"🔗 **Link:**\n`{final_link}`"
    )

    markup = get_file_buttons(log_msg_id, final_link, user_id, is_protected)
    if message_to_edit:
        await message_to_edit.edit_text(caption, reply_markup=markup)
    else:
        await client.send_message(chat_id, caption, reply_markup=markup)

# --- REUSE PREVIOUS CALLBACK HANDLERS ---
# (Note: Ensure callback handlers call send_updated_message with log_msg_id)
