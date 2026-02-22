import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users

# --- STATE MANAGEMENT ---
CLONE_SESSION = {}

# --- HELPER: Extract Channel ID ---
def parse_channel_input(text: str):
    text = text.strip()
    
    if "t.me/+" in text or "joinchat" in text:
        return "INVITE_LINK_ERROR"

    if re.match(r"^-100\d+$", text):
        return int(text)
    
    # Private Post Link (e.g. t.me/c/123456/1 -> -100123456)
    private_link_match = re.search(r"t\.me\/c\/(\d+)\/", text)
    if private_link_match:
        return int(f"-100{private_link_match.group(1)}")

    # Public Username
    username_match = re.search(r"(?:t\.me\/|@)(\w{5,32})", text)
    if username_match:
        name = username_match.group(1)
        if name != "c":
            return f"@{name}"
        
    return None

# --- 1. START CLONE PROCESS ---
@Client.on_message(filters.command("clone") & filters.private)
async def clone_init(client, message):
    user_id = message.from_user.id
    CLONE_SESSION[user_id] = {"step": "WAIT_TOKEN"}
    
    await message.reply_text(
        "🤖 **Clone Bot Creation Wizard**\n\n"
        "1️⃣ **Create a Bot:** Go to @BotFather and create a new bot.\n"
        "2️⃣ **Send Token:** Copy the API Token and send it here.\n\n"
        "_(Send /cancel to stop)_",
        reply_markup=ForceReply(selective=True, placeholder="12345:ABC-DEF...")
    )

# --- 2. HANDLE INPUTS ---
@Client.on_message(filters.private & filters.text & ~filters.command(["start", "clone", "stats", "broadcast"]))
async def clone_wizard_handler(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in CLONE_SESSION:
        return 
        
    session = CLONE_SESSION[user_id]
    text = message.text.strip()

    if text.lower() == "/cancel":
        del CLONE_SESSION[user_id]
        return await message.reply("🚫 **Operation Cancelled.**")

    # --- STEP 1: VALIDATE TOKEN ---
    if session["step"] == "WAIT_TOKEN":
        if not re.match(r"\d+:[\w-]{35}", text):
            return await message.reply("❌ **Invalid Bot Token.**\nPlease copy the correct token from @BotFather.")
        
        session["token"] = text
        session["step"] = "WAIT_CHANNEL"
        
        await message.reply_text(
            "✅ **Token Accepted!**\n\n"
            "Now I need a **Log Channel** to store your files.\n\n"
            "1️⃣ Create a **Private Channel**.\n"
            "2️⃣ **Add your new clone bot** as an **Admin** in that channel.\n"
            "3️⃣ Send any message in that channel.\n"
            "4️⃣ **Copy the Link** to that message and paste it here.\n"
            "_(e.g., `https://t.me/c/123456/1`)_",
            reply_markup=ForceReply(selective=True, placeholder="https://t.me/c/...")
        )

    # --- STEP 2: START BOT & VERIFY CHANNEL ---
    elif session["step"] == "WAIT_CHANNEL":
        channel_input = parse_channel_input(text)
        
        if channel_input == "INVITE_LINK_ERROR":
            return await message.reply("❌ **Invite Links are NOT supported!**\nPlease send a **Post Link**.")

        if not channel_input:
            return await message.reply("❌ **Invalid Format.**\nPlease send a valid **Post Link** (e.g., `https://t.me/c/xxx/1`).")
        
        msg = await message.reply("⚙️ **Verifying Channel Access...**")
        
        try:
            # 1. Start the Clone Bot
            new_client, error_msg = await start_clone(session["token"], user_id, channel_input)
            
            if not new_client:
                return await msg.edit(f"❌ **Error:** The Bot Token seems invalid.\nError: `{error_msg}`")

            # 2. Verify Channel Access
            final_channel_id = None
            try:
                # FIXED: Use get_chat instead of get_dialogs
                # get_chat works for Private Channel IDs if the bot is an Admin
                chat_info = await new_client.get_chat(channel_input)
                final_channel_id = chat_info.id
                
                # Send Test Message to confirm Write Access
                await new_client.send_message(final_channel_id, "✅ **Database Connected Successfully!**")
                
                # Update client with resolved ID
                new_client.log_channel = final_channel_id

            except Exception as e:
                await new_client.stop()
                return await msg.edit(
                    f"❌ **Channel Access Error:**\n\n"
                    f"The bot could not verify access to the channel.\n\n"
                    "**Possible Fixes:**\n"
                    "1. Ensure the Clone Bot is an **Admin** in the channel.\n"
                    "2. If it's a private channel, you might need to send a message **in the channel** first so the bot registers it.\n"
                    "3. Try sending the **Channel ID** directly (e.g. -100xxxx).\n\n"
                    f"Error: `{e}`"
                )

            # 3. Save to DB
            await clones_col.insert_one({
                "token": session["token"], 
                "user_id": user_id, 
                "username": new_client.me.username,
                "log_channel": final_channel_id
            })
            
            del CLONE_SESSION[user_id]
            
            await msg.edit(
                f"🎉 **Bot Created Successfully!**\n\n"
                f"🤖 **Bot:** @{new_client.me.username}\n"
                f"📢 **DB Channel:** `{final_channel_id}`\n\n"
                "You can now use your own bot to store files!"
            )
            
        except Exception as e:
            if user_id in CLONE_SESSION: del CLONE_SESSION[user_id]
            await msg.edit(f"❌ **System Error:** {e}")

# --- OTHER COMMANDS ---

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message):
    users = await users_col.count_documents({})
    clones = await clones_col.count_documents({})
    await message.reply_text(f"**📊 Bot Stats**\n\nUsers: {users}\nClones: {clones}")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_IDS) & filters.reply)
async def broadcast_handler(client, message):
    msg = await message.reply("📡 Broadcasting...")
    count = 0
    async for user in users_col.find():
        try:
            await message.reply_to_message.copy(chat_id=user['user_id'])
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            pass
    await msg.edit(f"✅ Broadcast complete to {count} users.")
