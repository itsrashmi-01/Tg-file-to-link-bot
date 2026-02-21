import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from config import Config
from bot.utils import is_subscribed, get_seconds
from bot.clone import db

files_col = db.files
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
    for msg in messages:
        log_msg = await msg.copy(chat_id=Config.LOG_CHANNEL_ID)
        media = msg.document or msg.video or msg.audio
        await save_file_to_db(msg, log_msg, media)
        link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        links_text += f"• [{getattr(media, 'file_name', 'File')}]({link})\n"
    await client.send_message(chat_id, links_text, disable_web_page_preview=True)

async def process_file(client, message):
    try:
        log_msg = await message.copy(chat_id=Config.LOG_CHANNEL_ID)
        media = message.document or message.video or message.audio
        await save_file_to_db(message, log_msg, media)

        stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        file_name = getattr(media, "file_name", "file")
        file_size = getattr(media, "file_size", 0)
        
        def humanbytes(b):
            if not b: return ""
            for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
                if b < 1024: return f"{b:.2f}{unit}B"
                b /= 1024
            return f"{b:.2f}PiB"

        caption = (
            f"📂 **File Name:** `{file_name}`\n"
            f"ℹ️ **Size:** {humanbytes(file_size)}\n\n"
            f"🔗 **Direct Download Link:**\n"
            f"`{stream_link}`"
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Open Link", url=stream_link), InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={stream_link}&text=Check+out+this+file!")],
            [InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{log_msg.id}"), InlineKeyboardButton("🔒 Protect", callback_data=f"protect_{log_msg.id}")],
            [InlineKeyboardButton("⏳ Set Validity", callback_data=f"validity_{log_msg.id}")]
        ])
        
        await message.reply_text(caption, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

async def save_file_to_db(user_msg, log_msg, media):
    await files_col.insert_one({
        "user_id": user_msg.from_user.id,
        "log_msg_id": log_msg.id,
        "file_name": getattr(media, "file_name", "file"),
        "file_size": getattr(media, "file_size", 0),
        "file_unique_id": media.file_unique_id,
        "timestamp": user_msg.date,
        "expire_at": None # No expiration by default
    })

# --- BUTTON CALLBACKS ---

@Client.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client, callback_query):
    await callback_query.message.reply_text("📝 **Enter new file name:**", reply_markup=ForceReply(selective=True))

@Client.on_callback_query(filters.regex(r"^protect_"))
async def protect_callback(client, callback_query):
    await callback_query.message.reply_text("🔒 **Enter password for this link:**", reply_markup=ForceReply(selective=True))

@Client.on_callback_query(filters.regex(r"^validity_"))
async def validity_callback(client, callback_query):
    await callback_query.message.reply_text(
        "⏳ **Enter validity period:**\n"
        "Examples: `10m` (10 minutes), `1h` (1 hour), `1d` (1 day), `1w` (1 week)", 
        reply_markup=ForceReply(selective=True)
    )

# --- TEXT REPLY HANDLER ---

@Client.on_message(filters.private & filters.reply)
async def reply_handler(client, message):
    reply = message.reply_to_message
    if not reply or not reply.reply_markup: return

    if isinstance(reply.reply_markup, ForceReply):
        text = reply.text
        action = "unknown"
        
        if "Enter new file name" in text: action = "rename"
        elif "Enter password" in text: action = "protect"
        elif "Enter validity period" in text: action = "validity"
        
        if action != "unknown":
            # Get last file uploaded by user (Simple State Management)
            last_file = await files_col.find_one({"user_id": message.from_user.id}, sort=[('_id', -1)])
            
            if last_file:
                if action == "rename":
                    await files_col.update_one({"_id": last_file["_id"]}, {"$set": {"file_name": message.text}})
                    await message.reply(f"✅ **Renamed to:** `{message.text}`")
                
                elif action == "protect":
                    await files_col.update_one({"_id": last_file["_id"]}, {"$set": {"password": message.text}})
                    await message.reply(f"🔒 **Password set:** `{message.text}`")
                
                elif action == "validity":
                    seconds = get_seconds(message.text)
                    if seconds:
                        expire_time = time.time() + seconds
                        await files_col.update_one({"_id": last_file["_id"]}, {"$set": {"expire_at": expire_time}})
                        await message.reply(f"⏳ **Link will expire in:** `{message.text}`\nFile will be auto-deleted.")
                    else:
                        await message.reply("❌ **Invalid format!** Use 10m, 1h, 1d etc.")
            else:
                await message.reply("❌ Error: File not found.")
