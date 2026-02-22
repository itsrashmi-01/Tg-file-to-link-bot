from pyrogram.types import Message

def get_file_id(file):
    return file.file_id

def get_file_name(file):
    if hasattr(file, "file_name"):
        return file.file_name
    return "file"

def get_file_size(file):
    if hasattr(file, "file_size"):
        return str(file.file_size)
    return "0"

class TgFileStreamer:
    def __init__(self, client, file, from_bytes, until_bytes):
        self.client = client
        self.file = file
        self.from_bytes = from_bytes
        self.until_bytes = until_bytes

    async def yield_chunks(self):
        # Calculate offset and length
        offset = self.from_bytes
        length = self.until_bytes - self.from_bytes + 1
        
        # Pyrogram's stream_media automatically handles chunks
        async for chunk in self.client.stream_media(
            self.file,
            offset=offset,
            limit=length
        ):
            yield chunk
