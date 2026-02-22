import math
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse

class TgFileStreamer:
    @staticmethod
    async def get_file_properties(client, file_id):
        file = await client.get_messages(None, file_id) # Usually retrieved from log channel
        return file

    @staticmethod
    async def byte_streamer(client, file_id, start, end, file_size):
        async for chunk in client.stream_media(file_id, offset=start, limit=end - start + 1):
            yield chunk

async def render_file(client, file_id, range_header: str):
    # Simplified Logic: In production, fetch metadata from DB first
    file_size = 100 * 1024 * 1024 # Placeholder
    start, end = 0, file_size - 1
    
    if range_header:
        range_str = range_header.replace("bytes=", "")
        parts = range_str.split("-")
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else file_size - 1

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Type": "video/mp4", # Dynamic based on extension
    }
    
    return StreamingResponse(
        TgFileStreamer.byte_streamer(client, file_id, start, end, file_size),
        status_code=206 if range_header else 200,
        headers=headers
    )
