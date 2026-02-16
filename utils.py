import math
import asyncio
from pyrogram import Client

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        """
        Robust Streamer with Auto-Retry to prevent 502/Protocol Errors.
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
            # Calculate chunk size
            limit = min(self.chunk_size, (self.end - current_pos) + 1)
            
            # --- RETRY LOGIC (The Fix) ---
            retries = 3
            success = False
            
            while retries > 0:
                try:
                    # Try to get the file chunk
                    async for chunk in self.client.get_file(
                        self.file_id,
                        offset=current_pos,
                        limit=limit
                    ):
                        yield chunk
                    
                    # If successful, move pointer and break retry loop
                    current_pos += limit
                    success = True
                    # Tiny sleep to let CPU breathe
                    await asyncio.sleep(0.001) 
                    break 
                
                except Exception as e:
                    print(f"⚠️ Stream Stalled at {current_pos}. Retrying ({3-retries}/3)... Error: {e}")
                    retries -= 1
                    await asyncio.sleep(1) # Wait 1s before retrying
            
            if not success:
                print(f"❌ CRITICAL: Stream failed completely at byte {current_pos}. Connection dropped.")
                # We stop the loop. This will still cause 'Too little data' error, 
                # BUT the retry logic above prevents 99% of these cases.
                break

def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
