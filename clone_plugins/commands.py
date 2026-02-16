from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from config import Config

async def start_fn(client, message):
    # Role Check: Is this the Owner?
    if message.from_user.id == client.OWNER_ID:
        await message.reply_text(
            f"👑 **Owner Panel**\n"
            f"I am active and saving files to `{client.LOG_CHANNEL}`"
        )
    else:
        # Check for Deep Link (Download)
        if len(message.command) > 1:
            file_hash = message.command[1]
            link = f"{Config.BASE_URL}/dl/{client.BOT_ID}/{file_hash}"
            await message.reply_text(f"🔗 **Download Link:** {link}")
        else:
            await message.reply_text("👋 I am a File Store Bot.")

# Export the handler to be registered by CloneManager
start_handler = MessageHandler(start_fn, filters.command("start") & filters.private)