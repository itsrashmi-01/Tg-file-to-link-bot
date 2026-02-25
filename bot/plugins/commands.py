import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from bot.clone import start_clone, stop_clone, clones_col, db
from config import Config

users_col = db.users

# --- CLONE SETUP FLOW ---

@Client.on_callback_query(filters.regex("clone_info"))
async def clone_instructions(client, callback_query):
    """Step 1: Instructions"""
    text = (
        "🤖 **Clone Bot Setup Guide**\n\n"
        "Follow these simple steps to create your own bot:\n\n"
        "1️⃣ **Get Token:** Create a bot at @BotFather and copy the API Token.\n"
        "2️⃣ **Prepare Channel:** Create a Private Channel (your database).\n"
        "3️⃣ **Finalize:** You will add your bot as admin and send a command there.\n\n"
        "Ready to start?"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Start Setup", callback_data="get_token")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_menu")]
    ])
    await callback_query.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("get_token"))
async def ask_for_token(client, callback_query):
    """Step 2: Ask for Token"""
    await users_col.update_one(
        {"user_id": callback_query.from_user.id}, 
        {"$set": {"state": "WAITING_FOR_TOKEN"}}
    )
    await callback_query.message.reply_text(
        "📝 **Step 1:** Paste your **Bot Token** from @BotFather below.\n\n"
        "*(Ensure you are replying to this message)*",
        reply_markup=ForceReply(placeholder="123456789:ABCDEF...")
    )
    await callback_query.message.delete()

@Client.on_message(filters.private & filters.text & ~filters.command(["start", "clone", "delete_clone"]))
async def clone_input_handler(client, message):
    """Handles the transition from Token to Channel link"""
    user = await users_col.find_one({"user_id": message.from_user.id})
    state = user.get("state") if user else None

    if state == "WAITING_FOR_TOKEN":
        token = message.text.strip()
        status = await message.reply("🔍 **Verifying Token...**")
        
        try:
            # Start clone immediately with dummy channel ID to listen for /connect
            new_clone = await start_clone(token, message.from_user.id, 0)
            
            if new_clone:
                await users_col.update_one(
                    {"user_id": message.from_user.id}, 
                    {"$set": {"state": "WAITING_FOR_CHANNEL", "temp_token": token}}
                )
                
                text = (
                    f"✅ **Bot @{new_clone.me.username} is Online!**\n\n"
                    "🛰 **Step 2: Connect your Database**\n\n"
                    f"1. Add @{new_clone.me.username} to your Private Channel as **Admin**.\n"
                    "2. **Inside that Channel**, send the command: `/connect`\n\n"
                    "✨ *I will automatically detect the channel and finish setup!*"
                )
                await status.edit(text)
            else:
                await status.edit("❌ **Invalid Token!** Please check @BotFather and try again.")
        except Exception as e:
            await status.edit(f"❌ **Connection Error:** `{e}`")

# --- THE HANDSHAKE: HANDLES /CONNECT IN CHANNELS ---

@Client.on_message(filters.command("connect") & (filters.group | filters.channel))
async def channel_connect_handler(client, message):
    """
    This runs on the CLONE bot instance when /connect is sent in the log channel.
    """
    owner_id = getattr(client, "owner_id", None)
    if not owner_id: return

    user = await users_col.find_one({"user_id": owner_id})
    if not user or user.get("state") != "WAITING_FOR_CHANNEL":
        return

    channel_id = message.chat.id
    token = user.get("temp_token")

    # 1. Verification post in channel
    await message.reply(f"✅ **Database Linked!**\nID: `{channel_id}`\nOwner ID: `{owner_id}`")

    # 2. Save everything to DB
    await clones_col.update_one(
        {"user_id": owner_id},
        {"$set": {
            "token": token, 
            "log_channel": channel_id, 
            "username": client.me.username,
            "active": True
        }},
        upsert=True
    )

    # 3. Finalize User State
    await users_col.update_one({"user_id": owner_id}, {"$set": {"state": "IDLE"}})

    # 4. Notify user in Private
    try:
        await client.send_message(
            owner_id, 
            f"🎊 **Setup Complete!**\n\nYour bot @{client.me.username} is now fully connected to your channel.\n\n"
            "You can now send files to your bot to generate direct links!"
        )
    except: pass

# --- UTILITY COMMANDS ---

@Client.on_message(filters.command("delete_clone") & filters.private)
async def delete_clone_handler(client, message):
    user_id = message.from_user.id
    clone = await clones_col.find_one({"user_id": user_id})
    if not clone:
        return await message.reply("❌ You don't have an active clone bot.")

    msg = await message.reply("🗑️ **Deleting your bot instance...**")
    try:
        await stop_clone(user_id)
        await clones_col.delete_one({"user_id": user_id})
        await msg.edit("✅ **Clone deleted successfully.**")
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message):
    u = await users_col.count_documents({})
    c = await clones_col.count_documents({})
    await message.reply_text(f"**📊 Stats**\n\nUsers: `{u}`\nClones: `{c}`")
