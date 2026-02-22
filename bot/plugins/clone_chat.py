import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from bot.clone import start_clone, stop_clone, clones_col
from config import Config

# Dictionary to store user states temporarily
USER_STATES = {}

# --- HELPER: SMART ID FIXER ---
def fix_channel_id(raw_id: str) -> int:
    """
    Attempts to fix common ID errors for private channels.
    1. Removes spaces.
    2. If it's a large positive number (common copy-paste error), adds -100.
    """
    clean_id = str(raw_id).replace(" ", "").strip()
    
    # Check if it is a number
    if not clean_id.lstrip("-").isdigit():
        raise ValueError("Not a number")

    # If it's a positive number and long (likely a channel ID missing prefix)
    if clean_id.isdigit() and len(clean_id) > 9:
        return int(f"-100{clean_id}")
    
    return int(clean_id)

# --- 1. ENTRY POINT ---
@Client.on_callback_query(filters.regex("clone_info"))
async def start_clone_process(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    existing_bot = await clones_col.find_one({"user_id": user_id})
    if existing_bot:
        await callback_query.answer("⚠️ You already have a clone bot!", show_alert=True)
        return

    text = (
        "🤖 **Create Your Own Bot**\n\n"
        "**Step 1:**\n"
        "• Go to @BotFather and create a new bot.\n"
        "• Copy the **API Token**.\n\n"
        "👇 **Now, send me the Bot Token:**"
    )
    
    USER_STATES[user_id] = {"step": "WAIT_TOKEN"}
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_clone")]
        ])
    )

# --- 2. CANCEL HANDLER ---
@Client.on_callback_query(filters.regex("cancel_clone"))
async def cancel_clone(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in USER_STATES:
        del USER_STATES[user_id]
    
    await callback_query.message.edit_text(
        "❌ **Process Cancelled.**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="start_menu")]])
    )

# --- 3. MESSAGE HANDLER (State Machine) ---
@Client.on_message(filters.private & filters.text & ~filters.command("start"))
async def clone_conversation_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state["step"]

    # --- STEP A: HANDLE TOKEN INPUT ---
    if step == "WAIT_TOKEN":
        token = message.text.strip()
        
        if ":" not in token or len(token) < 20:
            await message.reply("❌ **Invalid Token.**\nPlease check and send again, or /cancel.")
            return

        USER_STATES[user_id]["token"] = token
        USER_STATES[user_id]["step"] = "WAIT_CHANNEL"

        await message.reply(
            "✅ **Token Accepted!**\n\n"
            "**Step 2:**\n"
            "• Create a **Private Channel** (Log Channel).\n"
            "• Add your new bot to that channel as an **Administrator**.\n"
            "• Send me the **Channel ID**.\n\n"
            "**⚠️ IMPORTANT:**\n"
            "Private Channel IDs must start with `-100`.\n"
            "Example: `-1001234567890`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_clone")]
            ])
        )

    # --- STEP B: HANDLE CHANNEL ID INPUT ---
    elif step == "WAIT_CHANNEL":
        raw_id = message.text.strip()
        
        try:
            # Attempt to fix the ID automatically
            channel_id = fix_channel_id(raw_id)
        except ValueError:
            await message.reply("❌ **Invalid ID.** Please send a numeric ID (e.g., `-100xxxx`).")
            return

        token = state["token"]
        # Inform user if we auto-fixed the ID
        fix_msg = f" (Auto-fixed to `{channel_id}`)" if str(channel_id) != raw_id else ""
        status_msg = await message.reply(f"⚙️ **Booting up...**\nVerifying ID{fix_msg}...")

        # --- CALL THE CLONE FUNCTION ---
        try:
            # 1. Start the Bot Client
            client_instance = await start_clone(token, user_id, channel_id)
            
            if client_instance:
                bot_info = await client_instance.get_me()
                
                # 2. TEST CONNECTION: Send Msg to Log Channel
                try:
                    await client_instance.send_message(
                        channel_id,
                        "**🤖 System Notification**\n\n"
                        "✅ **Databases Connected Successfully.**\n"
                        "Your Clone Bot is now linked to this Log Channel."
                    )
                except Exception as e:
                    # IF FAIL: Stop bot, don't save, show EXACT error
                    await stop_clone(user_id)
                    await status_msg.edit_text(
                        f"❌ **Connection Failed!**\n\n"
                        f"**Error Details:**\n`{str(e)}`\n\n"
                        f"**Attempted Channel ID:** `{channel_id}`\n\n"
                        "**Checklist:**\n"
                        "1. Is the ID correct? (Did you copy it from a URL?)\n"
                        "2. Is the bot an **Admin** in the channel?\n"
                        "3. Does the bot have 'Post Messages' permission?",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_clone")]
                        ])
                    )
                    return # Stop here
                
                # 3. IF SUCCESS: Save to MongoDB
                await clones_col.insert_one({
                    "user_id": user_id,
                    "token": token,
                    "log_channel": channel_id,
                    "username": bot_info.username,
                    "first_name": bot_info.first_name
                })
                
                await status_msg.edit_text(
                    f"✅ **Success! Your bot is online.**\n\n"
                    f"🤖 **Bot:** @{bot_info.username}\n"
                    f"📡 **Log Channel:** Connected `{channel_id}`\n\n"
                    f"__Click /start in your new bot to begin.__"
                )
                del USER_STATES[user_id]
            else:
                await status_msg.edit_text("❌ **Failed to start.** Invalid Bot Token.")
                
        except Exception as e:
            await status_msg.edit_text(f"❌ **System Error:** `{str(e)}`")
            del USER_STATES[user_id]
