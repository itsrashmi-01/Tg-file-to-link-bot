from aiohttp import web
from . import Bot
from config import Config

routes = web.RouteTableDef()

@routes.get("/")
async def root_route(request):
    return web.json_response({"status": "running", "msg": "Bot is active"})

@routes.get("/dl/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        
        # Get message from Log Channel
        # We must use the Log Channel ID because private chat IDs are not accessible to public users
        message = await Bot.get_messages(chat_id=Config.LOG_CHANNEL_ID, message_ids=message_id)
        
        if not message or not message.media:
            return web.Response(status=404, text="File not found or deleted.")

        file_name = "file.bin"
        file_size = 0
        
        if message.document:
            file_name = message.document.file_name
            file_size = message.document.file_size
        elif message.video:
            file_name = message.video.file_name or "video.mp4"
            file_size = message.video.file_size
        elif message.audio:
            file_name = message.audio.file_name or "audio.mp3"
            file_size = message.audio.file_size

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Length": str(file_size)
        }
        
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)

        # Stream the file directly from Telegram servers to the user
        async for chunk in Bot.stream_media(message):
            await response.write(chunk)
            
        return response
        
    except Exception as e:
        return web.Response(status=500, text=f"Server Error: {e}")

async def web_server():
    app = web.Application()
    app.add_routes(routes)
    return app