import asyncio
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pyrogram import Client
from config import Config

# 1. Initialize FastAPI
app = FastAPI()

# 2. Initialize Bot (Don't start it yet)
bot = Client(
    "file_streamer",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="bot/plugins"),
    in_memory=True  # Helpful for Render's ephemeral file system
)

@app.get("/")
async def health():
    return {"status": "active", "info": "High-Speed Streamer Online"}

@app.get("/download/{msg_id}")
async def stream_file(msg_id: int, request: Request):
    try:
        msg = await bot.get_messages(Config.LOG_CHANNEL, msg_id)
        if not msg or not (msg.document or msg.video or msg.audio):
            raise HTTPException(status_code=404, detail="File not found")

        file = msg.document or msg.video or msg.audio
        
        async def file_generator():
            async for chunk in bot.stream_media(msg):
                yield chunk

        return StreamingResponse(
            file_generator(),
            media_type=file.mime_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'attachment; filename="{file.file_name}"',
                "Content-Length": str(file.file_size)
            }
        )
    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def start_services():
    # Start the Pyrogram Client
    await bot.start()
    print("Bot Started Successfully!")

    # Configure and Start Uvicorn
    port = int(os.environ.get("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    # This is the critical fix for Python 3.12+ 
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        pass
