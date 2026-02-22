import aiohttp
from pyrogram.errors import UserNotParticipant
from config import Config

class TgFileStreamer:
    def __init__(self, client, file_id, start_offset=0):
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

# --- TINYURL HELPER ---
async def get_tinyurl(long_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://tinyurl.com/api-create.php?url={long_url}") as response:
                return await response.text()
    except Exception as e:
        print(f"TinyURL Error: {e}")
        return long_url
