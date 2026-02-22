import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import PeerIdInvalid, ChannelInvalid, ChatWriteForbidden, RPCError
from bot.clone import start_clone, stop_clone, clones_col
from config import Config

# Dictionary to store user states temporarily
USER_STATES = {}

# --- HELPER: SMART ID FIXER ---
def fix_channel_id(raw_id: str) -> int:
    clean_id = str(raw_id).replace(" ", "").strip()
    if not clean_id.lstrip("-").isdigit():
        raise ValueError("Not a number")
    if clean_id.isdigit():
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

# --- 3. MESSAGE HANDLER ---
@Client.on_message(filters.private & ~filters.command("start"))
async def clone_conversation_handler(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in USER_STATES:
        return

    state = USER_STATES[user_id]
    step = state["step"]

    # --- STEP A: HANDLE TOKEN INPUT ---
    if step == "WAIT_TOKEN":
        if not message.text:
             await message.reply("❌ **Invalid Token.** Please send text only.")
             return

        token = message.text.strip()
        
        if ":" not in token or len(token) < 20:
            await message.reply("❌ **Invalid Token.**\nPlease check and send again, or /cancel.")
            return

        USER_STATES[user_id]["token"] = token
        USER_STATES[user_id]["step"] = "WAIT_CHANNEL"

        await message.reply(
            "✅ **Token Accepted!**\n\n"
            "**Step 2:**\n"
            "• Add your new bot to your Log Channel as an **Admin**.\n"
            "• **Forward a message** from that channel to me.\n"
            "• (Or send the Channel ID manually).\n\n"
            "__Tip: Forwarding is recommended to avoid ID errors.__",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_clone")]
            ])
        )

    # --- STEP B: HANDLE CHANNEL ID INPUT ---
    elif step == "WAIT_CHANNEL":
        channel_id = None
        
        # 1. DETECT ID (Forward or Text)
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
        elif message.text:
            try:
                channel_id = fix_channel_id(message.text.strip())
            except ValueError:
                pass 
        
        if not channel_id:
            await message.reply(
                "❌ **Could not detect Channel ID.**\n\n"
                "Please **Forward a message** from your Log Channel to me.\n"
                "Make sure the bot is an Admin so I can see the ID."
            )
            return

        token = state["token"]
        status_msg = await message.reply(f"⚙️ **Booting up...**\nTarget ID: `{channel_id}`")

        try:
            # 1. Start the Bot Client
            client_instance = await start_clone(token, user_id, channel_id)
            
            if not client_instance:
                await status_msg.edit_text("❌ **Failed to start.** Invalid Bot Token.")
                return

            bot_info = await client_instance.get_me()
            
            # 2. CRITICAL FIX: CACHE HANDSHAKE
            # We explicitly 'get_chat' to force Pyrogram to resolve the Peer ID
            # This fixes "Peer id invalid" for fresh sessions.
            try:
                chat_info = await client_instance.get_chat(channel_id)
                # Optional: Double check if bot is admin
                # permissions = chat_info.permissions ...
            except PeerIdInvalid:
                await stop_clone(user_id)
                await status_msg.edit_text(
                    f"❌ **Access Denied (Peer Invalid)**\n\n"
                    f"The bot @{bot_info.username} cannot see the channel `{channel_id}`.\n\n"
                    "**Solution:**\n"
                    "1. Go to your Channel.\n"
                    "2. Remove the bot and **Add it again** as Admin.\n"
                    "3. Send a message in the channel.\n"
                    "4. Try again here."
                )
                return
            except Exception as e:
                # If get_chat fails, we can't proceed
                await stop_clone(user_id)
                await status_msg.edit_text(f"❌ **Connection Error:** `{str(e)}`\nMake sure the bot is an Admin.")
                return

            # 3. TEST SENDING MESSAGE
            try:
                await client_instance.send_message(
                    channel_id,
                    "**🤖 System Notification**\n\n"
                    "✅ **Databases Connected Successfully.**\n"
                    "Your Clone Bot is now linked to this Log Channel."
                )
            except ChatWriteForbidden:
                 await stop_clone(user_id)
                 await status_msg.edit_text(
                    "❌ **Permission Error!**\n\n"
                    "I found the channel, but **cannot send messages**.\n"
                    "👉 Please ensure your bot is an **Admin** with 'Post Messages' rights."
                 )
                 return
            
            # 4. SUCCESS - SAVE TO DB
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
                f"📡 **Log Channel:** Connected `{channel_id}`\n"
                f"📨 **Test Message:** Sent\n\n"
                f"__Click /start in your new bot to begin.__"
            )
            del USER_STATES[user_id]

        except Exception as e:
            await stop_clone(user_id)
            await status_msg.edit_text(f"❌ **System Error:** `{str(e)}`")
            del USER_STATES[user_id]
