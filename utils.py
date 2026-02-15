import math
from pyrogram import Client

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, start_offset: int = 0, chunk_size: int = 1024 * 1024):
        self.client = client
        self.file_id = file_id
        self.offset = start_offset
        self.chunk_size = chunk_size

    async def __aiter__(self):
        """
        This generator yields chunks of the file from Telegram.
        """
        # We need to get the file location first
        # Ideally, we pass the file_location object directly if possible, 
        # but for simplicity in Pyrogram 2.x, we iterate via download_media generator
        
        # Pyrogram's stream_media method is the key here
        async for chunk in self.client.stream_media(
            self.file_id,
            limit=0, # 0 means download whole file
            offset=self.offset
        ):
            yield chunk