import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from config import Config
from bot.clone import db

BATCH_DATA = {}

def humanbytes(b):
    if not b: return ""
    for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
        if b < 1024: return f"{b:.2f}{unit}B"
        b /= 1024
    return f"{b:.2f}PiB"

def get_log_channel(client):
    if hasattr(client, "log_channel") and client.log_channel: return client.log_channel
    if Config.LOG_CHANNEL_ID: return int(Config.LOG_CHANNEL_ID)
    return None

def get_file_buttons(msg_id, link, is_protected=False):
    protect_text = "📝 Edit Password" if is_protected else "🔒 Protect"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Open Link", url=link), InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={link}&text=File")],
        [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{msg_id}"), InlineKeyboardButton(protect_text, callback_data=f"protect_{msg_id}")],
        [InlineKeyboardButton("⏳ Set Validity", callback_data=f"validity_{msg_id}")]
    ])

@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def file_handler(client, message):
    try:
        from bot.plugins.commands import CLONE_SESSION
        if message.from_user.id in CLONE_SESSION: return 
    except: pass

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
    target_channel = get_log_channel(client)
    if not target_channel: return await client.send_message(chat_id, "❌ **Error:** No DB Channel.")
    
    links_text = "**📦 Batch Links:**\n\n"
    for msg in messages:
        try:
            media = msg.document or msg.video or msg.audio or msg.photo
            if not media: continue
            file_name = getattr(media, "file_name", "Photo.jpg")
            file_size = getattr(media, "file_size", 0)
            log_msg = await msg.copy(chat_id=target_channel)
            await save_file_to_db(msg, log_msg, media, file_name, file_size)
            base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
            links_text += f"• [{file_name}]({base_link})\n"
        except: pass
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message):
    try:
        target_channel = get_log_channel(client)
        if not target_channel: return await message.reply("❌ **Error:** No DB Channel Configured.")
        
        media = message.document or message.video or message.audio or message.photo
        file_name = getattr(media, "file_name", "Photo.jpg") if not message.photo else f"Photo_{message.id}.jpg"
        file_size = getattr(media, "file_size", 0)

        try: log_msg = await message.copy(chat_id=target_channel)
        except Exception as e: return await message.reply(f"❌ **Channel Error:** Ensure Admin rights.\n`{e}`")

        await save_file_to_db(message, log_msg, media, file_name, file_size)
        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        await message.reply_text(
            f"✅ **Link Generated!**\n📂 `{file_name}`\n🔗 `{base_link}`",
            reply_markup=get_file_buttons(log_msg.id, base_link),
            quote=True
        )
    except Exception as e:
        print(f"Error: {e}")
        await message.reply_text(f"❌ Error: `{e}`")

async def save_file_to_db(user_msg, log_msg, media, file_name, file_size):
    unique_id = getattr(media, "file_unique_id", None) or getattr(media, "file_id", None)
    await db.files.insert_one({
        "user_id": user_msg.from_user.id,
        "log_msg_id": log_msg.id,
        "file_name": file_name,
        "file_size": file_size,
        "file_unique_id": unique_id,
        "timestamp": time.time(),
        "password": None,
        "expiry": None
    })

@Client.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await client.send_message(callback_query.message.chat.id, "📝 **New Name:**", reply_markup=ForceReply(selective=True, placeholder=f"rename_{file_id}"))

@Client.on_callback_query(filters.regex(r"^protect_"))
async def protect_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await client.send_message(callback_query.message.chat.id, "🔒 **Password:**", reply_markup=ForceReply(selective=True, placeholder=f"protect_{file_id}"))
    await callback_query.message.delete()

@Client.on_callback_query(filters.regex(r"^validity_"))
async def validity_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("30m", callback_data=f"settime_{file_id}_30m"), InlineKeyboardButton("1h", callback_data=f"settime_{file_id}_1h")],
        [InlineKeyboardButton("1d", callback_data=f"settime_{file_id}_1d"), InlineKeyboardButton("Back", callback_data=f"back_{file_id}")]
    ])
    await callback_query.message.edit_text("⏳ **Select Validity:**", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^settime_"))
async def set_validity_handler(client, callback_query):
    _, file_id, duration = callback_query.data.split("_")
    seconds = {"30m": 1800, "1h": 3600, "1d": 86400}.get(duration, 0)
    await db.files.update_one({"log_msg_id": int(file_id)}, {"$set": {"expiry": time.time() + seconds}})
    await callback_query.answer("✅ Done!", show_alert=True)
    await send_updated_message(client, callback_query.message.chat.id, int(file_id), message_to_edit=callback_query.message)

@Client.on_callback_query(filters.regex(r"^back_"))
async def back_to_main_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await send_updated_message(client, callback_query.message.chat.id, file_id, message_to_edit=callback_query.message)

@Client.on_message(filters.private & filters.reply)
async def input_handler(client, message):
    reply = message.reply_to_message
    if not reply or not reply.reply_markup or not isinstance(reply.reply_markup, ForceReply): return
    placeholder = reply.reply_markup.placeholder
    if not placeholder or "_" not in placeholder: return
    
    action, file_id = placeholder.split("_")
    file_id = int(file_id)
    file_data = await db.files.find_one({"log_msg_id": file_id})
    if not file_data: return await message.reply("❌ File not found.")

    try: 
        await message.delete()
        await reply.delete()
    except: pass

    if action == "rename":
        await db.files.update_one({"_id": file_data["_id"]}, {"$set": {"file_name": message.text}})
        await client.send_message(message.chat.id, f"✅ **Renamed:** `{message.text}`", delete_after=5)
    elif action == "protect":
        await db.files.update_one({"_id": file_data["_id"]}, {"$set": {"password": message.text}})
        await client.send_message(message.chat.id, f"🔐 **Password Set.**", delete_after=5)

    await send_updated_message(client, message.chat.id, file_id)

async def send_updated_message(client, chat_id, file_id, message_to_edit=None):
    file_data = await db.files.find_one({"log_msg_id": file_id})
    if not file_data: return
    base_link = f"{Config.BLOGGER_URL}?id={file_id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{file_id}"
    caption = f"✅ **Updated!**\n📂 `{file_data.get('file_name')}`\n🔗 `{base_link}`"
    markup = get_file_buttons(file_id, base_link, bool(file_data.get("password")))
    if message_to_edit: await message_to_edit.edit_text(caption, reply_markup=markup)
    else: await client.send_message(chat_id, caption, reply_markup=markup)
