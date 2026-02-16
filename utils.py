import math
import asyncio
from pyrogram import Client

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        """
        Optimized Telegram file streamer for low-RAM environments.
        """
        self.client = client
        self.file_id = file_id
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
            try:
                # Use get_file for stable streaming
                async for chunk in self.client.get_file(
                    self.file_id,
                    offset=current_pos,
                    limit=limit
                ):
                    yield chunk
                
                current_pos += limit
                # Tiny sleep to prevent CPU freeze on free tier
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"❌ Stream Error at byte {current_pos}: {e}")
                break

def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"