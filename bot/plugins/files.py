import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from bot.utils import is_subscribed

# Global Dictionary for Batching: { media_group_id: [messages] }
BATCH_DATA = {}

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def file_handler(client, message):
    # --- 1. Force Subscribe Check ---
    if not await is_subscribed(client, message.from_user.id):
        return await message.reply_text(
            "⚠️ **You must join our channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_URL)],
                [InlineKeyboardButton("Try Again", url=f"https://t.me/{client.me.username}?start=start")]
            ])
        )

    # --- 2. Batch Processing Logic ---
    if message.media_group_id:
        # If this is part of an album
        mg_id = message.media_group_id
        if mg_id not in BATCH_DATA:
            BATCH_DATA[mg_id] = []
            asyncio.create_task(process_batch(client, mg_id, message.chat.id))
        
        BATCH_DATA[mg_id].append(message)
        return

    # Normal Single File Processing
    await process_file(client, message)

async def process_batch(client, mg_id, chat_id):
    await asyncio.sleep(4) # Wait for all files in album to arrive
    messages = BATCH_DATA.pop(mg_id, [])
    
    links_text = "**📦 Batch Links:**\n\n"
    
    for msg in messages:
        # Forward to Log Channel
        log_msg = await msg.copy(chat_id=Config.LOG_CHANNEL_ID)
        link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        fname = msg.document.file_name if msg.document else "File"
        links_text += f"• [{fname}]({link})\n"
    
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message):
    try:
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        
        if Config.BLOGGER_URL:
            stream_link = f"{Config.BLOGGER_URL}?id={log_msg.id}"
        else:
            stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        
        await message.reply_text(
            f"**File Name:** `{message.document.file_name if message.document else 'File'}`\n"
            f"**Download Link:**\n{stream_link}",
            quote=True
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
