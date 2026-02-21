import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.clone import db
from config import Config

# Database Collections
users_col = db.users
auth_codes_col = db.auth_codes

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 1. CHECK FOR LOGIN VERIFICATION (Web App Login) ---
    if len(message.command) > 1:
        payload = message.command[1]
        
        if payload.startswith("login_"):
            token = payload.replace("login_", "")
            
            # Find the pending token and verify it
            result = await auth_codes_col.update_one(
                {"token": token, "status": "pending"},
                {"$set": {
                    "status": "verified",
                    "user_id": message.from_user.id,
                    "user_info": {
                        "id": message.from_user.id,
                        "first_name": message.from_user.first_name,
                        "username": message.from_user.username or ""
                    },
                    "role": "admin" if message.from_user.id in Config.ADMIN_IDS else "user"
                }}
            )
            
            if result.modified_count > 0:
                await message.reply("✅ **Login Successful!**\n\nYou can now return to your browser.", quote=True)
            else:
                await message.reply("❌ **Link Expired or Already Used.**", quote=True)
            return

    # --- 2. STANDARD START MESSAGE ---
    # Save User to DB for Stats
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except Exception:
        pass

    # Send Welcome Message
    await message.reply_text(
        "**Welcome!**\n\n"
        "Send me any file to get a direct download link.\n\n"
        "**Features:**\n"
        "• `/clone bot_token` - Create your own bot\n"
        "• `/protect password` - Reply to a file to set a password\n"
        "• **Web Dashboard:** Click the menu button to manage files.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 My Dashboard", web_app={"url": Config.BLOGGER_URL or Config.BASE_URL})]
        ]),
        quote=True
    )
