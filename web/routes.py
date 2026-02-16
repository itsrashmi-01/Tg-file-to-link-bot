from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database.files import file_db
from bot import bot_client # Needs to be exported from bot/__init__.py

router = APIRouter()

@router.get("/api/info/{hash_id}")
async def get_info(hash_id: str):
    """Blogger calls this to get file details"""
    file = await file_db.get_file(hash_id)
    if not file: return {"error": "File not found"}
    
    # Increase view count
    await file_db.inc_view(hash_id)
    
    return {
        "name": file["file_name"],
        "size": file["file_size"],
        "views": file["views"],
        # Direct stream link
        "stream_url": f"/stream/{hash_id}" 
    }

@router.get("/stream/{hash_id}")
async def stream_file(hash_id: str):
    file = await file_db.get_file(hash_id)
    if not file: raise HTTPException(404)

    async def streamer():
        async for chunk in bot_client.stream_media(file["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{file["file_name"]}"'}
    )