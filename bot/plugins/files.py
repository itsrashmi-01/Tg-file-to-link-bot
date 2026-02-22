import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from config import Config
from bot.clone import db

BATCH_DATA = {}

def get_log_channel(client):
    if hasattr(client, "log_channel") and client.log_channel: return client.log_channel
    if Config.LOG_CHANNEL_ID: return int(Config.LOG_CHANNEL_ID)
    return None

def get_file_buttons(msg_id, link):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Open Link", url=link), InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={link}")]])

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
    links = ""
    for msg in messages:
        try:
            media = msg.document or msg.video or msg.audio or msg.photo
            if not media: continue
            file_name = getattr(media, "file_name", "Photo.jpg")
            file_size = getattr(media, "file_size", 0)
            log_msg = await msg.copy(chat_id=target_channel)
            await save_file_to_db(msg, log_msg, media, file_name, file_size)
            base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
            links += f"• [{file_name}]({base_link})\n"
        except: pass
    await client.send_message(chat_id, f"**Batch Links:**\n{links}", disable_web_page_preview=True)

async def process_file(client, message):
    try:
        target_channel = get_log_channel(client)
        if not target_channel: return await message.reply("❌ **Error:** No DB Channel Configured.")
        media = message.document or message.video or message.audio or message.photo
        file_name = getattr(media, "file_name", "Photo.jpg") if not message.photo else f"Photo_{message.id}.jpg"
        file_size = getattr(media, "file_size", 0)
        log_msg = await message.copy(chat_id=target_channel)
        await save_file_to_db(message, log_msg, media, file_name, file_size)
        base_link = f"{Config.BLOGGER_URL}?id={log_msg.id}" if Config.BLOGGER_URL else f"{Config.BASE_URL}/dl/{log_msg.id}"
        await message.reply_text(f"✅ **Link:** `{base_link}`", reply_markup=get_file_buttons(log_msg.id, base_link))
    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")

async def save_file_to_db(user_msg, log_msg, media, file_name, file_size):
    unique_id = getattr(media, "file_unique_id", None) or getattr(media, "file_id", None)
    await db.files.insert_one({"user_id": user_msg.from_user.id, "log_msg_id": log_msg.id, "file_name": file_name, "file_size": file_size, "file_unique_id": unique_id, "timestamp": time.time()})
