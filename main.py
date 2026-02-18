import asyncio
import os
from pyrogram import Client
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from config import Config
import uvicorn

app = FastAPI()
bot = Client(
    "file_streamer",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins")
)

@app.get("/")
async def health():
    return {"status": "active"}

@app.get("/download/{msg_id}")
async def stream_file(msg_id: int):
    try:
        # Get message from Log Channel
        msg = await bot.get_messages(Config.LOG_CHANNEL, msg_id)
        if not msg or not (msg.document or msg.video or msg.audio):
            raise HTTPException(status_code=404, detail="File not found")

        file = msg.document or msg.video or msg.audio
        
        # Generator function to stream file in chunks
        async def file_generator():
            async for chunk in bot.stream_media(msg):
                yield chunk

        return StreamingResponse(
            file_generator(),
            media_type=file.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file.file_name}"',
                "Content-Length": str(file.file_size)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    await bot.start()
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
