import asyncio
import logging
import uvloop

# --- FIX START ---
# We must set the event loop policy and create a loop BEFORE importing Pyrogram
# because Pyrogram checks for an event loop immediately upon import.
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# --- FIX END ---

from aiohttp import web
from pyrogram import idle
from bot import Bot
from bot.server import web_server
from clone_bot import clone_manager
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def start_services():
    print("---------------------------------")
    print("      Starting Telegram Bot      ")
    print("---------------------------------")

    # 1. Start Main Bot
    await Bot.start()
    me = await Bot.get_me()
    print(f"✅ Main Bot Started: @{me.username}")
    
    # 2. Start Clone Bots
    await clone_manager.start_clones()
    
    # 3. Start Web Server
    app = await web_server()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    print(f"✅ Server Running on Port {Config.PORT}")
    print(f"🔗 Base URL: {Config.BASE_URL}")

    # Keep running
    await idle()
    
    # Cleanup
    print("Stopping Services...")
    await clone_manager.stop_clones()
    await Bot.stop()
    print("❌ Bots Stopped")

if __name__ == "__main__":
    try:
        # We reuse the loop created at the top
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal Error: {e}")
