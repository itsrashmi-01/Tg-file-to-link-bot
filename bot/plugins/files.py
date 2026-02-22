import asyncio
from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
# Removed 'get_hash' to prevent ImportErrors if it's missing in utils
from bot.utils import get_file_id, get_file_name, get_file_size
from config import Config
from bot.clone import db

files_col = db.files

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def file_handler(client, message):
    # --- 1. GET LOG CHANNEL ---
    # Safe access to log_channel attribute (handles both Main Bot and Clones)
    user_log_channel = getattr(client, "log_channel", None)
    
    # If it's the Main Bot, user_log_channel is None, so we use Config.
    # If it's a Clone, user_log_channel should be set.
    log_channel = user_log_channel or Config.LOG_CHANNEL_ID

    # If NO channel is found (Clone not connected, or Main Bot config missing)
    if not log_channel:
        try:
            await message.reply(
                "❌ **Database Not Connected.**\n\n"
                "Please add me to your Log Channel and use `/connect` inside that channel first.",
                quote=True
            )
        except:
            pass
        return

    # --- 2. COLLECT FILE INFO ---
    file = getattr(message, message.media.value)
    file_name = get_file_name(file)
    file_size = get_file_size(file)
    file_id = get_file_id(file)
    
    # --- 3. SAVE TO LOG CHANNEL ---
    try:
        # Copy message to the specific Log Channel
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
    file_data = {
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "message_id": log_msg.id,
        "channel_id": log_channel, # Critical for streaming
        "user_id": message.from_user.id,
        "caption": message.caption or ""
    }
    
    # Use insert_one (async)
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
