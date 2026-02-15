from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import UserNotParticipant
from config import Config

async def get_fsub_status(client: Client, message: Message):
    """
    Checks if the user has joined the Force Sub Channel.
    Returns True if joined (or if FSub is disabled), False otherwise.
    """
    if not Config.FORCE_SUB_CHANNEL or Config.FORCE_SUB_CHANNEL == 0:
        return True  # Feature is disabled

    user_id = message.from_user.id
    try:
        # Check if user is a member
        member = await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        if member.status in ["banned", "kicked"]:
            await message.reply_text("🚫 **You are banned from using this bot.**")
            return False
    except UserNotParticipant:
        # User is NOT a member -> Send "Please Join" message
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "You must join our Update Channel to use this bot.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=Config.FORCE_SUB_LINK)],
                [InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.me.username}?start=start")]
            ])
        )
        return False
    except Exception as e:
        # If bot is not admin in that channel, it might fail
        print(f"FSub Error: {e}")
        return True # Let them pass if there's an error (fail-safe)

    return True
