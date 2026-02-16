import math
import asyncio
from pyrogram import Client, raw, errors
from pyrogram.file_id import FileId, FileType
from pyrogram.raw.types import InputDocumentFileLocation, InputPhotoFileLocation

class TgFileStreamer:
    def __init__(self, client: Client, file_id: str, file_size: int, range_header: str = None):
        self.client = client
        self.file_id = file_id
        self.file_size = file_size
        self.chunk_size = 1024 * 1024  # 1MB Chunks
        
        self.decoded = FileId.decode(file_id)
        self.start = 0
        self.end = file_size - 1

        if range_header:
            try:
                ranges = range_header.replace("bytes=", "").split("-")
                self.start = int(ranges[0]) if ranges[0] else 0
                if len(ranges) > 1 and ranges[1]:
                    self.end = int(ranges[1])
            except: pass

    def get_location(self):
        # Re-construct location (vital for retries)
        if self.decoded.file_type == FileType.PHOTO:
            return InputPhotoFileLocation(
                id=self.decoded.media_id,
                access_hash=self.decoded.access_hash,
                file_reference=self.decoded.file_reference,
                thumb_size=self.decoded.thumbnail_source
            )
        return InputDocumentFileLocation(
            id=self.decoded.media_id,
            access_hash=self.decoded.access_hash,
            file_reference=self.decoded.file_reference,
            thumb_size=""
        )

    async def __aiter__(self):
        current_pos = self.start
        
        while current_pos <= self.end:
            limit = min(self.chunk_size, (self.end - current_pos) + 1)
            retries = 5
            
            while retries > 0:
                try:
                    # 1. Try to Download Chunk
                    r = await self.client.invoke(
                        raw.functions.upload.GetFile(
                            location=self.get_location(),
                            offset=current_pos,
                            limit=limit
                        ),
                        sleep_threshold=30
                    )
                    
                    if isinstance(r, raw.types.upload.File):
                        chunk = r.bytes
                    else:
                        chunk = b""

                    if not chunk: break 

                    yield chunk
                    current_pos += len(chunk)
                    break # Success, move to next chunk
                
                except errors.FileMigrate as e:
                    # 2. HANDLE DC MIGRATION (The [303] Fix)
                    print(f"🌍 Switching DC: {e.dc_id}")
                    await self.client.session.switch_dc(e.dc_id)
                    continue # Retry immediately on new DC
                    
                except Exception as e:
                    # 3. Handle Network Drops
                    print(f"⚠️ Retry {current_pos}: {e}")
                    retries -= 1
                    await asyncio.sleep(1)
            
            if retries == 0:
                print("❌ Stream failed after retries")
                break

def human_readable_size(size_bytes):
    if not size_bytes: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
