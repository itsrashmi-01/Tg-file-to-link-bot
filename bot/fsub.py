
from pyrogram.errors import UserNotParticipant
from config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def get_fsub_status(client, message):
    if not Config.FORCE_SUB_CHANNEL:
        return True
    
    user_id = message.from_user.id
    try:
        await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Join Update Channel", url=Config.FORCE_SUB_LINK)
        ]])
        await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our update channel to use this bot.",
            reply_markup=buttons
        )
        return False
    except Exception:
        return True # Fail open if error