@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def file_handler(client, message):
    status = await message.reply("🔄 **Archiving...**", quote=True)
    
    try:
        # 1. Forward to Log Channel
        log = await message.copy(Config.LOG_CHANNEL)
        media = getattr(log, log.media.value)
        
        # 2. Save Metadata
        data = {
            "file_id": media.file_id,
            "file_name": getattr(media, "file_name", "unknown"),
            "file_size": getattr(media, "file_size", 0),
            "mime_type": getattr(media, "mime_type", "application/octet-stream")
        }
        hash_id = await file_db.add_file(data)
        
        blogger_link = f"{Config.BLOG_URL}?id={hash_id}"
        await status.edit_text(f"✅ **File Secured!**\n\n🔗 [Download Page]({blogger_link})")

    except Exception as e:
        # This will now tell you exactly what is wrong in Telegram
        await status.edit_text(f"❌ **Error:** `{str(e)}` \nCheck if the Bot is Admin in the Log Channel.")
