import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from bot.clone import start_clone, clones_col
from config import Config

# Dictionary to store user states temporarily
# Structure: { user_id: { "step": "WAIT_TOKEN", "data": {} } }
USER_STATES = {}

# --- 1. ENTRY POINT: Triggered by "Create Your Own Bot" button ---
@Client.on_callback_query(filters.regex("clone_info"))
async def start_clone_process(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    # Check if user already has a bot (Optional: limit to 1 bot per user)
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
    
    # Set State to WAIT_TOKEN
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
    
    # If user is not in a state, ignore
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state["step"]

    # --- STEP A: HANDLE TOKEN INPUT ---
    if step == "WAIT_TOKEN":
        token = message.text.strip()
        
        # Basic validation (Tokens usually contain a colon)
        if ":" not in token or len(token) < 20:
            await message.reply("❌ **Invalid Token.**\nPlease check and send again, or /cancel.")
            return

        # Save token and move to next step
        USER_STATES[user_id]["token"] = token
        USER_STATES[user_id]["step"] = "WAIT_CHANNEL"

        await message.reply(
            "✅ **Token Accepted!**\n\n"
            "**Step 2:**\n"
            "• Create a **Private Channel** (this will be your Log Channel).\n"
            "• Add your new bot (the one you just created) to that channel as an **Administrator**.\n"
            "• Send me the **Channel ID** (e.g., `-100123456789`).\n\n"
            "__Tip: You can use @idbot or forward a message from the channel to get the ID.__",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_clone")]
            ])
        )

    # --- STEP B: HANDLE CHANNEL ID INPUT ---
    elif step == "WAIT_CHANNEL":
        raw_id = message.text.strip()
        
        try:
            channel_id = int(raw_id)
            if not str(channel_id).startswith("-100"):
                await message.reply("⚠️ **Warning:** Channel IDs usually start with `-100`.\nAre you sure? If so, send it again. If not, check your ID.")
                # We don't return here, we let it pass if they insist, or you can force strict check
        except ValueError:
            await message.reply("❌ **Invalid ID.** It must be a number (e.g., `-100xxxx`).")
            return

        token = state["token"]
        status_msg = await message.reply("⚙️ **Booting up your bot...** Please wait.")

        # --- CALL THE CLONE FUNCTION ---
        try:
            # start_clone is imported from your bot/clone.py
            client_instance = await start_clone(token, user_id, channel_id)
            
            if client_instance:
                bot_info = await client_instance.get_me()
                
                # Save to Database
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
                    f"📡 **Log Channel:** `{channel_id}`\n\n"
                    f"__Click /start in your new bot to begin.__"
                )
                # Clear state
                del USER_STATES[user_id]
            else:
                await status_msg.edit_text(
                    "❌ **Failed to start.**\n\n"
                    "Possible reasons:\n"
                    "1. The Token is invalid.\n"
                    "2. The bot is NOT an Admin in the Log Channel.\n"
                    "3. The Log Channel ID is incorrect."
                )
        except Exception as e:
            await status_msg.edit_text(f"❌ **Error:** `{str(e)}`")
            del USER_STATES[user_id]
