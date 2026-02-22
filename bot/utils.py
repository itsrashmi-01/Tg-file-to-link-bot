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

# --- IMPROVED SHORTENER HELPER ---
async def get_short_link(long_url):
    if not Config.SHORTENER_URL or not Config.SHORTENER_API:
        return long_url # Return original if configs are missing

    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"{Config.SHORTENER_URL}?api={Config.SHORTENER_API}&url={long_url}"
            async with session.get(api_url) as response:
                data = await response.json()
                
                # Check for various success keys used by different shorteners
                if "shortenedUrl" in data:
                    return data["shortenedUrl"]
                elif "short_url" in data:
                    return data["short_url"]
                elif "url" in data:
                    return data["url"]
                
                # If API returns an error message
                print(f"Shortener API Error: {data}")
                return long_url
                
    except Exception as e:
        print(f"Shortener Connection Error: {e}")
        return long_url
