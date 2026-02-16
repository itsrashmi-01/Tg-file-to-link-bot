from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from database.files import file_db
from bot import bot_client

router = APIRouter()

@router.get("/api/info/{slug}")
async def get_file_info(slug: str):
    file = await file_db.get_file(slug)
    if not file:
        raise HTTPException(status_code=404)
    return {
        "name": file["file_name"],
        "size": file["file_size"],
        "dl_url": f"/api/download/{slug}"
    }

@router.get("/api/download/{slug}")
async def stream_file(slug: str):
    file = await file_db.get_file(slug)
    if not file:
        raise HTTPException(status_code=404)

    async def streamer():
        async for chunk in bot_client.stream_media(file["file_id"]):
            yield chunk

    return StreamingResponse(
        streamer(),
        media_type=file["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{file["file_name"]}"'}
    )
