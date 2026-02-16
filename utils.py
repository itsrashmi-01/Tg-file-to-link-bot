import math
import asyncio
from pyrogram import Client, raw
from pyrogram.file_id import FileId, FileType
from pyrogram.raw.types import InputDocumentFileLocation, InputPhotoFileLocation

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        self.client = client
        self.file_id = file_id
        self.file_size = file_size
        self.chunk_size = 1024 * 1024  # 1MB Chunks
        
        # Decode File ID to find location
        decoded = FileId.decode(file_id)
        
        if decoded.file_type == FileType.PHOTO:
             self.file_location = InputPhotoFileLocation(
                id=decoded.media_id,
                access_hash=decoded.access_hash,
                file_reference=decoded.file_reference,
                thumb_size=decoded.thumbnail_source
            )
        else:
            self.file_location = InputDocumentFileLocation(
                id=decoded.media_id,
                access_hash=decoded.access_hash,
                file_reference=decoded.file_reference,
                thumb_size=""
            )
        
        # Simple start position
        self.start = 0
        if range_header:
            try:
                self.start = int(range_header.replace("bytes=", "").split("-")[0])
            except: pass

    async def __aiter__(self):
        offset = self.start
        
        while True:
            try:
                # Direct call to Telegram
                chunk = await self.client.invoke(
                    raw.functions.upload.GetFile(
                        location=self.file_location,
                        offset=offset,
                        limit=self.chunk_size
                    ),
                    sleep_threshold=60
                )
                
                if not isinstance(chunk, raw.types.upload.File):
                    break # Stop if weird response
                
                data = chunk.bytes
                if not data:
                    break # Stop if no more data
                
                yield data
                offset += len(data)
                
            except Exception as e:
                print(f"Error streaming: {e}")
                await asyncio.sleep(1) # Wait a bit and retry same chunk
                continue

# Helper for file size display
def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
