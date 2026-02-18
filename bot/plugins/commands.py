from pyrogram import Client, filters
from bot.clone import start_clone, clones_col

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # Simplified text to prevent Entity Bounds Error
    await message.reply_text(
        "**Welcome!**\n\n"
        "Send me any file, and I will generate a direct download link.\n"
        "To create your own bot, use: `/clone bot_token`",
        quote=True
    )

@Client.on_message(filters.command("clone") & filters.private)
async def clone_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text("usage: `/clone bot_token`", quote=True)
    
    token = message.command[1]
    msg = await message.reply_text("♻️ **Creating Clone...**", quote=True)
    
    # Pass user_id to the start_clone function
    bot_info = await start_clone(token, message.from_user.id)
    
    if bot_info:
        await clones_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"token": token, "username": bot_info.username}},
            upsert=True
        )
        await msg.edit(f"✅ **Clone Created!**\nUsername: @{bot_info.username}")
    else:
        await msg.edit("❌ **Error:** Invalid Token or Bot already running.")
