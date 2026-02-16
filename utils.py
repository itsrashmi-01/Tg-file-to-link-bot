import math
import asyncio
from pyrogram import Client, raw
from pyrogram.file_id import FileId

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        """
        Streamer using Raw API to bypass Pyrogram get_file bugs.
        """
        self.client = client
        self.file_id = file_id
        self.file_size = file_size
        self.chunk_size = 1024 * 1024  # 1MB
        
        # Decode the File ID once to get the location
        decoded = FileId.decode(file_id)
        self.file_location = decoded.file_location
        self.dc_id = decoded.dc_id
        
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
            
            retries = 3
            success = False
            
            while retries > 0:
                try:
                    # RAW API CALL: GetFile
                    # This bypasses the buggy client.get_file() wrapper
                    r = await self.client.invoke(
                        raw.functions.upload.GetFile(
                            location=self.file_location,
                            offset=current_pos,
                            limit=limit
                        ),
                        sleep_threshold=30
                    )
                    
                    if isinstance(r, raw.types.upload.File):
                        chunk = r.bytes
                    elif isinstance(r, raw.types.upload.FileCdnRedirect):
                        # Handle CDN if necessary (rare for private files)
                        raise Exception("CDN Redirect not supported in simple streamer")
                    else:
                        raise Exception("Unknown response")

                    if not chunk:
                        break # End of file

                    yield chunk
                    current_pos += len(chunk)
                    success = True
                    await asyncio.sleep(0.001)
                    break
                
                except Exception as e:
                    print(f"⚠️ Stream Retry ({3-retries}): {e}")
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
