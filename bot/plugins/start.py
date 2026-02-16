from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.users import user_db
from bot.helpers.checks import check_fsub
from config import Config

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await user_db.add_user(message.from_user.id, message.from_user.first_name)
    
    if not await check_fsub(client, message.from_user.id):
        return await message.reply(
            "⚠️ **You must join our channel to use this bot!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/YourChannel")]
            ])
        )

    # If user passed a file hash (Deep Linking)
    if len(message.command) > 1:
        # We redirect them to the Web App (Blogger)
        hash_id = message.command[1]
        web_link = f"{Config.BLOG_URL}?id={hash_id}"
        return await message.reply(
            f"🔗 **Your Download Link is Ready!**\n\n[Click Here to Download]({web_link})",
            disable_web_page_preview=True
        )

    await message.reply("👋 **Welcome!** Send me any file to get a High-Speed Link.")