import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from bot.clone import start_clone, stop_clone, clones_col, db
from config import Config

users_col = db.users

# --- CLONE INTERACTIVE FLOW ---

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_instructions(client, callback_query):
    """Step 1: Provide Setup Instructions"""
    text = (
        "🤖 **Create Your Own Bot**\n\n"
        "Follow these steps to set up your personal instance:\n\n"
        "1️⃣ Create a bot at @BotFather and copy the **API Token**.\n"
        "2️⃣ Create a **Private Channel** to serve as your database.\n"
        "3️⃣ You will need to add your new bot as an **Admin** in that channel.\n\n"
        "Ready to begin?"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I'm Ready, Start Setup", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("get_token"))
async def ask_for_token(client, callback_query):
    """Step 2: Request the API Token"""
    await users_col.update_one(
        {"user_id": callback_query.from_user.id}, 
        {"$set": {"state": "WAITING_FOR_TOKEN"}}
    )
    await callback_query.message.reply_text(
        "📝 **Step 1:** Send me your **Bot Token** from @BotFather.",
        reply_markup=ForceReply(placeholder="123456789:ABCDEF...")
    )
    await callback_query.message.delete()

@Client.on_message(filters.private & filters.text & ~filters.command(["start", "clone", "delete_clone"]))
async def clone_input_handler(client, message):
    """Handles the multi-step input for Token and Channel ID"""
    user = await users_col.find_one({"user_id": message.from_user.id})
    state = user.get("state") if user else None

    # STEP 3: Verify Token and Ask for Channel ID
    if state == "WAITING_FOR_TOKEN":
        token = message.text.strip()
        status = await message.reply("🔍 **Verifying Bot Token...**")
        
        # Test the client temporarily to verify token validity
        try:
            temp_client = Client(":memory:", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=token, in_memory=True)
            await temp_client.start()
            bot_me = await temp_client.get_me()
            await temp_client.stop()
            
            # Token valid: Save token and move to next state
            await users_col.update_one(
                {"user_id": message.from_user.id}, 
                {"$set": {"state": "WAITING_FOR_CHANNEL", "temp_token": token}}
            )
            
            text = (
                f"✅ **Token Verified!** Bot: @{bot_me.username}\n\n"
                "🛰 **Step 2:** Provide your **Database Channel ID**.\n\n"
                f"1. Add @{bot_me.username} to your Private Channel as **Admin**.\n"
                "2. Send the Channel ID here (e.g., `-100123456789`)."
            )
            await status.edit(text, reply_markup=ForceReply(placeholder="-100..."))
            
        except Exception as e:
            await status.edit(f"❌ **Invalid Token!**\n\nPlease ensure you copied the full token from @BotFather and try again.\n\n`Error: {e}`")

    # STEP 4: Verify Channel Access and Complete Setup
    elif state == "WAITING_FOR_CHANNEL":
        try:
            channel_id = int(message.text.strip())
            token = user.get("temp_token")
            status = await message.reply("⚙️ **Finalizing Setup...**")
            
            # Attempt to start the actual clone instance
            new_clone = await start_clone(token, message.from_user.id, channel_id)
            
            if new_clone:
                try:
                    # Test admin permissions in the user's channel
                    await new_clone.send_message(channel_id, "✅ **Database Connected!**\n\nYour personal bot is now ready to store files.")
                except Exception:
                    await stop_clone(message.from_user.id)
                    return await status.edit(f"❌ **Permission Error!**\n\nYour bot must be an **Admin** in channel `{channel_id}` to work. Grant permissions and try again.")

                # Success: Reset state and save clone to DB
                await clones_col.update_one(
                    {"user_id": message.from_user.id},
                    {"$set": {"token": token, "log_channel": channel_id, "username": new_clone.me.username}},
                    upsert=True
                )
                await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"state": "IDLE"}})
                
                await status.edit(f"🎊 **Congratulations!**\n\nYour bot @{new_clone.me.username} is now active.")
            else:
                await status.edit("❌ **Error:** Failed to initialize the bot. Please restart the process.")
        except ValueError:
            await message.reply("❌ **Invalid ID!** Please send a numeric Channel ID (starts with -100).")

# --- ADMIN & UTILITY COMMANDS ---

@Client.on_message(filters.command("delete_clone") & filters.private)
async def delete_clone_handler(client, message):
    user_id = message.from_user.id
    clone = await clones_col.find_one({"user_id": user_id})
    if not clone:
        return await message.reply("❌ You don't have an active clone bot.")

    msg = await message.reply("🗑️ **Shutting down your bot...**")
    try:
        await stop_clone(user_id)
        await clones_col.delete_one({"user_id": user_id})
        await msg.edit("✅ **Clone Deleted Successfully.**")
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message):
    users = await users_col.count_documents({})
    clones = await clones_col.count_documents({})
    await message.reply_text(f"**📊 Statistics**\n\n👤 Users: `{users}`\n🤖 Clones: `{clones}`")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_IDS) & filters.reply)
async def broadcast_handler(client, message):
    msg = await message.reply("📡 **Broadcasting...**")
    count = 0
    async for user in users_col.find():
        try:
            await message.reply_to_message.copy(chat_id=user['user_id'])
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await msg.edit(f"✅ Broadcast complete to `{count}` users.")
