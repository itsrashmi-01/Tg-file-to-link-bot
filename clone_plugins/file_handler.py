from pyrogram import filters, enums
from pyrogram.handlers import MessageHandler
from database.files_db import files_db
from config import Config

async def save_file_handler(client, message):
    # 1. Security Check: Only the Owner can add files
    if message.from_user.id != client.OWNER_ID:
        return

    status = await message.reply_text("🔄 **Processing...**\nForwarding to DB Channel...")

    try:
        # 2. THE MAGIC STEP: Forward to the DB Channel
        # This ensures the file exists even if the user deletes their message
        try:
            log_msg = await message.forward(chat_id=client.LOG_CHANNEL)
        except Exception as e:
            await status.edit_text(f"❌ **Error:** I cannot post in the DB Channel (`{client.LOG_CHANNEL}`).\nMake sure I am an **Admin** there!")
            return

        # 3. Extract the File Object
        # (Handles Documents, Videos, Audios, and Photos)
        media = log_msg.document or log_msg.video or log_msg.audio or log_msg.photo
        
        # Photos come as a list of sizes; we take the last (largest) one
        if isinstance(media, list):
            media = media[-1]

        # 4. Save Metadata to MongoDB
        file_hash = await files_db.save_file(
            bot_id=client.BOT_ID,
            media=media,
            caption=message.caption or ""
        )

        # 5. Generate the Download Link
        link = f"{Config.BASE_URL}/dl/{client.BOT_ID}/{file_hash}"
        
        # 6. Reply to Owner
        await status.edit_text(
            f"✅ **File Saved Successfully!**\n\n"
            f"📂 **File Name:** `{getattr(media, 'file_name', 'Photo')}`\n"
            f"💾 **Size:** `{getattr(media, 'file_size', 0) / 1024 / 1024:.2f} MB`\n\n"
            f"🔗 **Download Link:**\n`{link}`\n\n"
            f"🤖 **Shareable Bot Link:**\n`https://t.me/{client.me.username}?start={file_hash}`"
        )

    except Exception as e:
        await status.edit_text(f"❌ **Critical Error:** {e}")

# Register the handler
# It listens for ANY file type sent in private chat
file_handler = MessageHandler(
    save_file_handler, 
    (filters.document | filters.video | filters.audio | filters.photo) & filters.private
)
