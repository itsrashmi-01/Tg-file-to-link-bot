from pyrogram import Client, filters
from bot import db

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "**Main Bot Interface**\n\n"
        "Send me any file to get a direct download link.\n"
        "Want your own bot? Use `/clone <bot_token>`"
    )

@Client.on_message(filters.command("clone") & filters.private)
async def clone_command(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/clone 12345:ABC-DEF...`")
    
    token = message.command[1]
    user_id = message.from_user.id
    
    # Save to DB
    await db.clones.update_one(
        {"user_id": user_id},
        {"$set": {"token": token, "user_id": user_id}},
        upsert=True
    )
    
    await message.reply_text("✅ Clone Saved! Please restart the bot (admin only) or wait for auto-restart.")