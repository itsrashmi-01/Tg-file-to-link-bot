import math
import asyncio
from pyrogram import Client

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        self.client = client
        self.file_id = file_id
        self.file_size = file_size
        self.chunk_size = 1024 * 1024  # 1MB
        
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
            
            # RETRY LOGIC (Fixes "Too little data" / 502 Errors)
            retries = 10
            success = False
            
            while retries > 0:
                try:
                    # High-Level API: Automatically handles [303 FILE_MIGRATE]
                    async for chunk in self.client.get_file(
                        self.file_id,
                        offset=current_pos,
                        limit=limit
                    ):
                        yield chunk
                    
                    # If we reach here, the chunk is fully downloaded
                    current_pos += limit
                    success = True
                    await asyncio.sleep(0.001)
                    break 
                
                except Exception as e:
                    print(f"⚠️ Stream Retry ({10-retries}) at {current_pos}: {e}")
                    retries -= 1
                    await asyncio.sleep(1)
            
            if not success:
                print(f"❌ Critical Fail at {current_pos}")
                break

def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
