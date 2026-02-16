from pyrogram import Client
from config import Config
from clone_plugins.commands import start_handler
from clone_plugins.file_handler import file_handler

# Global Dictionary to keep bots alive in memory
RUNNING_BOTS = {}

class CloneManager:
    @staticmethod
    async def start_clone(token, channel_id, owner_id):
        bot_id = token.split(':')[0]
        
        if bot_id in RUNNING_BOTS:
            return True

        try:
            # 1. Initialize Client
            app = Client(
                name=f"clone_{bot_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=token,
                in_memory=True
            )

            # 2. Inject Context (So handlers know who the owner is)
            app.OWNER_ID = int(owner_id)
            app.LOG_CHANNEL = int(channel_id)
            app.BOT_ID = bot_id

            # 3. Manually Register Handlers (Modular approach)
            # This allows you to edit clone_plugins/ without touching this file
            app.add_handler(start_handler)
            app.add_handler(file_handler)

            # 4. Start
            await app.start()
            RUNNING_BOTS[bot_id] = app
            return True
        except Exception as e:
            print(f"Failed to start clone {bot_id}: {e}")
            return False

    @staticmethod
    def get_client(bot_id):
        return RUNNING_BOTS.get(bot_id)