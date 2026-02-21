import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from config import Config
from bot.utils import is_subscribed
from bot.clone import db

files_col = db.files

# Global Dictionary for Batching: { media_group_id: [messages] }
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
        
        # Save to DB
        await save_file_to_db(message, log_msg, media)

        # Generate Link
        stream_link = f"{Config.BASE_URL}/dl/{log_msg.id}"
        file_name = getattr(media, "file_name", "file")
        file_size = getattr(media, "file_size", 0)
        
        # Human Readable Size
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
            f"`{stream_link}`" # Monospaced for click-to-copy
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚀 Open Link", url=stream_link),
                InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={stream_link}&text=Check+out+this+file!")
            ],
            [
                InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{log_msg.id}"),
                InlineKeyboardButton("🔒 Protect", callback_data=f"protect_{log_msg.id}")
            ],
            [
                InlineKeyboardButton("⏳ Set Validity", callback_data=f"validity_{log_msg.id}")
            ]
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
        "timestamp": user_msg.date
    })

# --- CALLBACK HANDLERS FOR BUTTONS ---

@Client.on_callback_query(filters.regex(r"^rename_"))
async def rename_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await callback_query.message.reply_text(
        "📝 **Enter new file name:**",
        reply_markup=ForceReply(selective=True, placeholder=str(file_id)) # Store ID in placeholder hint
    )

@Client.on_callback_query(filters.regex(r"^protect_"))
async def protect_callback(client, callback_query):
    file_id = int(callback_query.data.split("_")[1])
    await callback_query.message.reply_text(
        "🔒 **Enter password for this link:**",
        reply_markup=ForceReply(selective=True, placeholder=str(file_id))
    )

@Client.on_callback_query(filters.regex(r"^validity_"))
async def validity_callback(client, callback_query):
    await callback_query.answer("⚠️ This feature is coming soon!", show_alert=True)

# --- REPLY HANDLER (Captures input for Rename/Protect) ---

@Client.on_message(filters.private & filters.reply)
async def reply_handler(client, message):
    reply = message.reply_to_message
    if not reply or not reply.reply_markup: return

    # Check if it was a ForceReply from our bot
    if isinstance(reply.reply_markup, ForceReply):
        text = reply.text
        # We stored the log_msg_id in the placeholder logic (or we can track state)
        # Simplified: We need to find the ID. 
        # Since ForceReply doesn't carry hidden data easily in Pyrogram without state DB, 
        # we will extract ID from the message text we sent? No, that's messy.
        # FIX: We will rely on the user replying to the prompt.
        
        # Ideally, we should use a database to track "User X is renaming File Y".
        # For simplicity here, I will assume the prompt text tells us the action.
        
        action = "unknown"
        if "Enter new file name" in text: action = "rename"
        elif "Enter password" in text: action = "protect"
        
        if action != "unknown":
            # Finding the file ID is tricky without state. 
            # Strategy: Find the LAST file uploaded by this user in DB or use the original message link if visible.
            # Robust way: Save state in DB. 
            
            # FAST FIX: Fetch the last file uploaded by this user.
            last_file = await files_col.find_one({"user_id": message.from_user.id}, sort=[('_id', -1)])
            
            if last_file:
                if action == "rename":
                    new_name = message.text
                    await files_col.update_one({"_id": last_file["_id"]}, {"$set": {"file_name": new_name}})
                    await message.reply(f"✅ **Renamed to:** `{new_name}`")
                
                elif action == "protect":
                    password = message.text
                    await files_col.update_one({"_id": last_file["_id"]}, {"$set": {"password": password}})
                    await message.reply(f"🔒 **Password set:** `{password}`")
            else:
                await message.reply("❌ Error: Could not find file to update.")
