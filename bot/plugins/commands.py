# ... (Keep existing imports) ...
from bot.clone import db

# ... (Keep existing setup) ...
auth_codes_col = db.auth_codes # Access the auth collection

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    # --- 1. CHECK FOR LOGIN VERIFICATION ---
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

    # --- 2. EXISTING START LOGIC ---
    # (Existing user tracking logic)
    try:
        await users_col.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )
    except Exception:
        pass

    await message.reply_text(
        "**Welcome!**\n\n"
        "Send me any file to get a link.\n"
        "Features:\n"
        "• `/clone bot_token` - Create your own bot\n"
        "• `/protect password` - Reply to a file to set a password",
        quote=True
    )
