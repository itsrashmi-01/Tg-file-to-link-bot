import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBot
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient

# DB Setup
db = AsyncIOMotorClient(Config.MONGO_URL).TelegramBotCluster
clones_col = db.cloned_bots

# Global dictionary
RUNNING_CLONES = {}

async def start_clone_bot(token, log_channel_input, session_string=None):
    try:
        # 1. Initialize Client
        if session_string:
            clone = Client(
                name=f":memory:{token}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=session_string,
                in_memory=True,
                plugins=dict(root="bot")
            )
        else:
            clone = Client(
                name=f":memory:{token}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=token,
                in_memory=True,
                plugins=dict(root="bot")
            )

        # 2. Start Client (With FloodWait Protection)
        try:
            await clone.start()
        except FloodWait as e:
            print(f"⚠️ FloodWait: Sleeping for {e.value}s...")
            await asyncio.sleep(e.value)
            await clone.start()
        except Exception as e:
            print(f"❌ Could not login clone (Token: {token[:10]}...): {e}")
            # If token is invalid, delete it to stop loops
            if "token is invalid" in str(e).lower():
                await clones_col.delete_one({"token": token})
                print(f"🗑️ Deleted Invalid Token Clone.")
            return None, None

        me = await clone.get_me()

        # 3. Save Session (Prevent future FloodWaits)
        if not session_string:
            try:
                new_session = await clone.export_session_string()
                await clones_col.update_one(
                    {"token": token},
                    {"$set": {"session_string": new_session}},
                    upsert=True
                )
                print(f"💾 Session Saved for @{me.username}")
            except Exception as e:
                print(f"⚠️ Failed to save session: {e}")

        # 4. Resolve Channel ID
        final_channel_id = None
        try:
            # Handle Integers vs Strings
            if isinstance(log_channel_input, int) or (isinstance(log_channel_input, str) and log_channel_input.lstrip("-").isdigit()):
                final_channel_id = int(log_channel_input)
            else:
                # Resolve Username
                chat = await clone.get_chat(log_channel_input)
                final_channel_id = chat.id
            
            # --- SELF-CHECK: Ensure we aren't messaging ourselves ---
            if final_channel_id == me.id:
                raise UserIsBot("Bot cannot be its own Log Channel")

            # Verify Admin permissions
            test = await clone.send_message(final_channel_id, ".")
            await test.delete()

        except UserIsBot:
            print(f"❌ ERROR: Clone @{me.username} is set to use ITSELF as a channel.")
            print("🗑️ Deleting broken clone data...")
            await clones_col.delete_one({"token": token})
            await clone.stop()
            return None, None

        except PeerIdInvalid:
            print(f"⚠️ Warning: Clone @{me.username} cannot access channel {log_channel_input}. (Not Admin?)")
            # We DON'T delete here, just warn. User can fix permissions later.
            final_channel_id = log_channel_input

        except Exception as e:
            print(f"❌ Error verifying channel for @{me.username}: {e}")
            final_channel_id = log_channel_input

        # 5. Success
        RUNNING_CLONES[me.id] = {
            "client": clone,
            "log_channel": final_channel_id
        }
        
        print(f"🚀 Started Clone: @{me.username}")
        return me, final_channel_id
        
    except Exception as e:
        print(f"❌ Fatal Error in start_clone_bot: {e}")
        return None, None

async def load_all_clones():
    print("🤖 Loading Clones...")
    count = 0
    # Use 'async for' to iterate
    async for bot_data in clones_col.find():
        token = bot_data.get('token')
        log_channel = bot_data.get('log_channel')
        session_string = bot_data.get('session_string')
        
        if token and log_channel:
            # Pass session string to avoid FloodWait
            bot, _ = await start_clone_bot(token, log_channel, session_string)
            if bot:
                count += 1
            # Small delay between loads to be safe
            await asyncio.sleep(1.5)
            
    print(f"✅ Loaded {count} Clone Bots.")
