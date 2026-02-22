import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from bot.clone import start_clone, stop_clone, clones_col, CLONE_BOTS
from config import Config

# Dictionary to store user states temporarily
USER_STATES = {}

# --- 1. ENTRY POINT ---
@Client.on_callback_query(filters.regex("clone_info"))
async def start_clone_process(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    # Check if user already has a bot
    existing_bot = await clones_col.find_one({"user_id": user_id})
    if existing_bot:
        # If they have a bot but no Log Channel, we let them proceed to fix it?
        # For now, just show the warning or Manage Menu
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

# --- 3. TOKEN HANDLER ---
@Client.on_message(filters.private & ~filters.command("start"))
async def clone_conversation_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state["step"]

    if step == "WAIT_TOKEN":
        if not message.text:
             await message.reply("❌ **Invalid Token.** Please send text only.")
             return

        token = message.text.strip()
        if ":" not in token or len(token) < 20:
            await message.reply("❌ **Invalid Token.**\nPlease check and send again.")
            return

        # --- START BOT IMMEDIATELY ---
        status_msg = await message.reply("⚙️ **Starting your bot...** Please wait.")
        
        try:
            # Stop any existing session for this user first
            await stop_clone(user_id)
            
            # Start without Log Channel initially
            client_instance = await start_clone(token, user_id, log_channel=None)
            
            if not client_instance:
                await status_msg.edit_text("❌ **Invalid Token.** Could not start bot.")
                return
            
            bot_info = await client_instance.get_me()
            
            # Save partial info to DB so the /connect command works
            await clones_col.update_one(
                {"user_id": user_id},
                {"$set": {
                    "token": token,
                    "username": bot_info.username,
                    "first_name": bot_info.first_name,
                    "log_channel": None # Pending
                }},
                upsert=True
            )
            
            del USER_STATES[user_id]
            
            # --- SHOW INSTRUCTIONS ---
            text = (
                f"✅ **Bot Started: @{bot_info.username}**\n\n"
                "**Final Step: Connect Database**\n"
                "1. Add your bot (@{bot_info.username}) to your **Log Channel** as an Admin.\n"
                "2. Go to that channel and send the command: `/connect`\n"
                "3. The bot will automatically detect the ID and save it.\n\n"
                "__Wait for the 'Connected' message in your channel.__"
            )
            
            await status_msg.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Done", callback_data="start_menu")]
                ])
            )

        except Exception as e:
            await status_msg.edit_text(f"❌ **System Error:** `{str(e)}`")
            del USER_STATES[user_id]
