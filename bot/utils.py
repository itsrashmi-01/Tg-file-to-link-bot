from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from config import Config

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, start_offset: int = 0):
        self.client = client
        self.file_id = file_id
        self.offset = start_offset

    async def __aiter__(self):
        async for chunk in self.client.stream_media(
            self.file_id,
            limit=0,
            offset=self.offset
        ):
            yield chunk

async def is_subscribed(client, user_id):
    if not Config.FORCE_SUB_CHANNEL:
        return True
    try:
        await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"FSub Error: {e}")
        return True

# --- NEW: Time Parser ---
def get_seconds(time_string):
    """Converts a string like '1h', '10m' to seconds."""
    get_time = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
        'mo': 2592000
    }
    try:
        unit = time_string[-1].lower()
        if unit not in get_time: return None
        val = int(time_string[:-1])
        return val * get_time[unit]
    except:
        return None
