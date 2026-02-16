from pyrogram.errors import UserNotParticipant
from config import Config

async def check_fsub(client, user_id):
    if not Config.FSUB_ID: return True
    try:
        member = await client.get_chat_member(Config.FSUB_ID, user_id)
        return member.status not in ["kicked", "left"]
    except UserNotParticipant:
        return False
    except:
        return True