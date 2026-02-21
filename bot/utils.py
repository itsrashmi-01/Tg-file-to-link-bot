from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from config import Config

class TgFileStreamer:
    # ... (Keep existing TgFileStreamer class) ...
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

# --- NEW HELPER ---
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
        return True # Fail safe
