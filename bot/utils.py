from pyrogram import Client
from typing import Union
from bot.clone import db

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, start_offset: int = 0):
        self.client = client
        self.file_id = file_id
        self.start_offset = start_offset
        self.bytes_yielded = 0

    async def __aiter__(self):
        async for chunk in self.client.stream_media(
            self.file_id,
            offset=self.start_offset
        ):
            self.bytes_yielded += len(chunk)
            yield chunk
