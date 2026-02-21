import aiohttp
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from config import Config

# --- EXISTING CODE ---
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

# --- NEW FUNCTION ---
async def get_tinyurl(long_url):
    url = f"http://tinyurl.com/api-create.php?url={long_url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    except Exception:
        return long_url # Fallback to original if failed
