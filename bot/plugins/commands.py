import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, InviteHashInvalid
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users

# --- STATE MANAGEMENT ---
CLONE_SESSION = {}

# --- HELPER: Extract Channel Info ---
def parse_channel_input(text: str):
    text = text.strip()
    
    # 1. Invite Link (Best for Private Channels)
    if "t.me/+" in text or "joinchat" in text:
        return {"type": "invite_link", "value": text}

    # 2. Direct ID
    if re.match(r"^-100\d+$", text):
        return {"type": "id", "value": int(text)}
    
    # 3. Private Post Link
    private_link_match = re.search(r"t\.me\/c\/(\d+)", text)
    if private_link_match:
        return {"type": "id", "value": int(f"-100{private_link_match.group(1)}")}

    # 4. Public Username
    username_match = re.search(r"(?:t\.me\/|@)(\w{5,32})", text)
    if username_match:
        name = username_match.group(1)
        if name != "c":
            return {"type": "username", "value": f"@{name}"}
        
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
            "Now I need access to your **Private Log Channel**.\n\n"
            "1️⃣ Create a **Private Channel**.\n"
            "2️⃣ Add your new clone bot as an **Admin**.\n"
            "3️⃣ **Create an Invite Link** for the channel.\n"
            "4️⃣ Paste the **Invite Link** here.\n"
            "_(e.g., `https://t.me/+AbCdEfG123...`)_",
            reply_markup=ForceReply(selective=True, placeholder="https://t.me/...")
        )

    # --- STEP 2: START BOT & VERIFY CHANNEL ---
    elif session["step"] == "WAIT_CHANNEL":
        channel_data = parse_channel_input(text)
        
        if not channel_data:
            return await message.reply("❌ **Invalid Format.**\nPlease send a valid **Invite Link**.")
        
        msg = await message.reply("⚙️ **Verifying Channel Access...**")
        
        # We need to pass a dummy ID (0) initially to start the client, 
        # then we resolve the real ID using the link.
        try:
            new_client, error_msg = await start_clone(session["token"], user_id, 0)
            
            if not new_client:
                return await msg.edit(f"❌ **Bot Start Error:**\nThe Token seems invalid.\nError: `{error_msg}`")

            # --- RESOLVE CHANNEL ID ---
            final_channel_id = None
            
            try:
                if channel_data["type"] == "invite_link":
                    # KEY FIX: Using join_chat resolves the peer ID for private channels
                    try:
                        chat = await new_client.join_chat(channel_data["value"])
                        final_channel_id = chat.id
                    except UserAlreadyParticipant:
                        # If already in, get_chat with the LINK usually works now
                        # Or we try to resolve via the Invite Link object
                        try:
                            # Parse link hash if possible or just use get_chat
                            chat = await new_client.get_chat(channel_data["value"])
                            final_channel_id = chat.id
                        except Exception as e:
                            # Fallback: Ask user for ID if link fails despite being participant
                            await new_client.stop()
                            return await msg.edit(f"⚠️ **Already Admin, but ID not found.**\n\nPlease send the **Channel ID** (e.g. -100...) instead of the link now.")
                
                elif channel_data["type"] == "id":
                    # Direct ID: Try explicit send to force-check
                    # If this fails with PeerInvalid, the user MUST use an Invite Link
                    final_channel_id = channel_data["value"]
                    await new_client.send_message(final_channel_id, "✅ **Database Connected!**")

                elif channel_data["type"] == "username":
                    chat = await new_client.get_chat(channel_data["value"])
                    final_channel_id = chat.id
                    await new_client.send_message(final_channel_id, "✅ **Database Connected!**")

                # --- SUCCESS: SAVE & UPDATE ---
                if final_channel_id:
                    # Update the running client's log channel
                    new_client.log_channel = final_channel_id
                    
                    # Save to DB
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
                else:
                    await new_client.stop()
                    await msg.edit("❌ **Error:** Could not resolve Channel ID. Please try a fresh Invite Link.")

            except Exception as e:
                await new_client.stop()
                return await msg.edit(
                    f"❌ **Channel Access Error:**\n\n"
                    f"Could not connect to the channel.\n\n"
                    "**Fix:**\n"
                    "1. Ensure the Clone Bot is **Admin**.\n"
                    "2. Use a **fresh Invite Link** (`t.me/+...`).\n"
                    f"Error: `{e}`"
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
