from pyrogram import Client

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, start_offset: int = 0):
        self.client = client
        self.file_id = file_id
        self.offset = start_offset

    async def __aiter__(self):
        # Stream chunks from Telegram
        async for chunk in self.client.stream_media(
            self.file_id,
            limit=0,
            offset=self.offset
        ):
            yield chunk