import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
# IMPORT get_tinyurl HERE
from bot.utils import is_subscribed, get_tinyurl 
from bot.clone import db 

files_col = db.files
users_col = db.users # Access Users DB

# Global Dictionary for Batching
BATCH_DATA = {}

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **You must join our channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_URL)],
                [InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start=start")]
            ])
        )

    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in BATCH_DATA:
            BATCH_DATA[mg_id] = []
            asyncio.create_task(process_batch(client, mg_id, message.chat.id))
        BATCH_DATA[mg_id].append(message)
        return

    await process_file(client, message)

async def process_batch(client, mg_id, chat_id):
    await asyncio.sleep(4)
    messages = BATCH_DATA.pop(mg_id, [])
    
    links_text = "**📦 Batch Links:**\n\n"
    
    # Check User Settings for Shortener
    user_data = await users_col.find_one({"user_id": chat_id})
    use_shortener = user_data.get("use_shortener", False) if user_data else False

    for msg in messages:
        log_msg = await msg.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        media = msg.document or msg.video or msg.audio
        await files_col.insert_one({
            "user_id": msg.from_user.id,
            "log_msg_id": log_msg.id,
            "file_name": getattr(media, "file_name", "file"),
            "file_size": getattr(media, "file_size", 0),
            "file_unique_id": media.file_unique_id,
            "timestamp": msg.date
        })

        link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        if use_shortener:
            link = await get_tinyurl(link) # Shorten if enabled

        fname = getattr(media, "file_name", "File")
        links_text += f"• [{fname}]({link})\n"
    
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message):
    try:
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        media = message.document or message.video or message.audio
        await files_col.insert_one({
            "user_id": message.from_user.id,
            "log_msg_id": log_msg.id,
            "file_name": getattr(media, "file_name", "file"),
            "file_size": getattr(media, "file_size", 0),
            "file_unique_id": media.file_unique_id,
            "timestamp": message.date
        })

        if Config.BLOGGER_URL:
            stream_link = f"{Config.BLOGGER_URL}?id={log_msg.id}"
        else:
            stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        # --- SHORTENER LOGIC ---
        user_data = await users_col.find_one({"user_id": message.from_user.id})
        if user_data and user_data.get("use_shortener"):
            status = await message.reply("🔗 Shortening link...")
            stream_link = await get_tinyurl(stream_link)
            await status.delete()
        # -----------------------

        await message.reply_text(
            f"**File Name:** `{getattr(media, 'file_name', 'File')}`\n"
            f"**Download Link:**\n{stream_link}",
            quote=True,
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
