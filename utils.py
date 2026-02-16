import math
import asyncio
from pyrogram import Client
from pyrogram.types import Message

class TgFileStreamer:
    def __init__(self, client: Client, media_object, file_size: int, range_header: str = None):
        """
        Updated to accept the Media Object directly (Fixes 'str object' error).
        """
        self.client = client
        self.media = media_object  # Store the object (Document/Video), NOT the string ID
        self.file_size = file_size
        self.chunk_size = 1024 * 1024  # 1MB chunks
        
        self.start = 0
        self.end = file_size - 1

        if range_header:
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                self.start = int(ranges[0]) if ranges[0] else 0
                if len(ranges) > 1 and ranges[1]:
                    self.end = int(ranges[1])
            except (ValueError, IndexError):
                pass

    async def __aiter__(self):
        current_pos = self.start
        while current_pos <= self.end:
            limit = min(self.chunk_size, (self.end - current_pos) + 1)
            
            # Retry Logic
            retries = 3
            success = False
            while retries > 0:
                try:
                    # PASS THE OBJECT (self.media), NOT THE STRING
                    async for chunk in self.client.get_file(
                        self.media,
                        offset=current_pos,
                        limit=limit
                    ):
                        yield chunk
                    
                    current_pos += limit
                    success = True
                    await asyncio.sleep(0.001)
                    break
                except Exception as e:
                    print(f"⚠️ Retry ({3-retries}): {e}")
                    retries -= 1
                    await asyncio.sleep(1)
            
            if not success:
                print(f"❌ Critical Stream Fail at {current_pos}")
                break

def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
