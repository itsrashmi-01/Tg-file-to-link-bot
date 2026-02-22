import asyncio
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.utils import get_file_id, get_file_name, get_file_size, get_hash
from config import Config
from bot.clone import db

files_col = db.files

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def file_handler(client, message):
    # --- 1. GET LOG CHANNEL ---
    # Check if this is a Clone (client.log_channel) or Main Bot (Config.LOG_CHANNEL_ID)
    log_channel = getattr(client, "log_channel", None) or Config.LOG_CHANNEL_ID

    if not log_channel:
        await message.reply(
            "❌ **Database Not Connected.**\n\n"
            "Please add me to your Log Channel and use `/connect` inside that channel first.",
            quote=True
        )
        return

    # --- 2. COLLECT FILE INFO ---
    file = getattr(message, message.media.value)
    file_name = get_file_name(file)
    file_size = get_file_size(file)
    file_id = get_file_id(file)
    
    # --- 3. SAVE TO LOG CHANNEL ---
    try:
        # We copy the message to the specific Log Channel of this bot
        log_msg = await message.copy(log_channel)
    except Exception as e:
        await message.reply(
            f"❌ **Error:** Could not save file.\n\n"
            f"Reason: `{e}`\n\n"
            "Make sure I am an **Admin** in your Log Channel with 'Post Messages' permission.",
            quote=True
        )
        return

    # --- 4. SAVE METADATA TO DB ---
    # CRITICAL: We now save 'channel_id' so the streamer knows where to find this file later
    file_data = {
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "message_id": log_msg.id,
        "channel_id": log_channel, # <--- Added this field
        "user_id": message.from_user.id,
        "caption": message.caption or ""
    }
    await files_col.insert_one(file_data)

    # --- 5. GENERATE LINKS ---
    stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📺 Watch / Stream", 
                web_app=WebAppInfo(url=stream_link)
            )
        ],
        [
            InlineKeyboardButton(
                "🚀 Fast Download", 
                url=stream_link
            )
        ]
    ])

    await message.reply_text(
        f"**📂 File Saved!**\n\n"
        f"**Name:** `{file_name}`\n"
        f"**Size:** `{file_size}`\n\n"
        f"__Click the button below to watch or download.__",
        reply_markup=buttons,
        quote=True
    )
