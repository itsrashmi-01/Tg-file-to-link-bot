import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from pyrogram.handlers import MessageHandler
from bot.clone import start_clone, clones_col, db
from config import Config

users_col = db.users

# --- STATE MANAGEMENT ---
CLONE_SESSION = {}

# --- HELPER: Extract Channel ID ---
def parse_channel_input(message: Message):
    text = message.text.strip() if message.text else ""
    
    # 1. Forwarded Message (Best)
    if message.forward_from_chat:
        return message.forward_from_chat.id
    
    # 2. Direct ID
    if re.match(r"^-100\d+$", text):
        return int(text)
    
    # 3. Private Post Link
    private_link_match = re.search(r"t\.me\/c\/(\d+)", text)
    if private_link_match:
        return int(f"-100{private_link_match.group(1)}")

    # 4. Public Username
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
@Client.on_message(filters.private & (filters.text | filters.forwarded) & ~filters.command(["start", "clone", "stats", "broadcast"]))
async def clone_wizard_handler(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in CLONE_SESSION:
        return 
        
    session = CLONE_SESSION[user_id]
    text = message.text.strip() if message.text else ""

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
            "Now I need your **Log Channel**.\n\n"
            "1️⃣ Create a **Private Channel**.\n"
            "2️⃣ **Add your new clone bot** as an Admin.\n"
            "3️⃣ **Forward a Message** from that channel to here.\n"
            "_(If forwarding doesn't work, send the Channel ID: -100...)_",
            reply_markup=ForceReply(selective=True, placeholder="Forward message here...")
        )

    # --- STEP 2: START BOT & VERIFY CHANNEL ---
    elif session["step"] == "WAIT_CHANNEL":
        channel_id = parse_channel_input(message)
        
        if not channel_id:
            return await message.reply("❌ **Invalid Format.**\nPlease **Forward a Message** from the channel or send the ID.")
        
        msg = await message.reply("⚙️ **Starting Bot...**")
        
        try:
            # 1. Start the Clone Bot (Dummy Channel ID 0 initially)
            new_client, error_msg = await start_clone(session["token"], user_id, 0)
            
            if not new_client:
                return await msg.edit(f"❌ **Bot Start Error:**\nThe Token seems invalid.\nError: `{error_msg}`")

            await msg.edit("⚙️ **Verifying Channel Access...**")

            # 2. Connection Logic
            try:
                # A. Try Simple Connection First
                chat_info = await new_client.get_chat(channel_id)
                final_channel_id = chat_info.id
                await new_client.send_message(final_channel_id, "✅ **Database Connected Successfully!**")
                
                # Success immediately? Save and finish.
                await save_and_finish(new_client, user_id, session["token"], final_channel_id, msg)
                return

            except Exception as e:
                # B. If failed (Peer Invalid), we need to "Discover" the channel
                await msg.edit(
                    "⚠️ **Almost there!**\n\n"
                    "I started your bot, but I can't see the channel yet.\n\n"
                    "👉 **Please go to your Channel and send a message.**\n"
                    "*(Type anything, e.g. 'hello')*\n\n"
                    "I am listening for it..."
                )

                # Define a temporary handler to catch the update
                future = asyncio.get_running_loop().create_future()

                async def discovery_handler(c, m):
                    # Check if the message is from the expected channel OR if the user added the bot
                    if m.chat.id == channel_id or (m.forward_from_chat and m.forward_from_chat.id == channel_id):
                        if not future.done():
                            future.set_result(m.chat.id)

                # Add handler to the NEW CLIENT
                handler = MessageHandler(discovery_handler)
                new_client.add_handler(handler)

                try:
                    # Wait up to 60 seconds for the user to send a message in the channel
                    found_chat_id = await asyncio.wait_for(future, timeout=60.0)
                    
                    # Found it!
                    new_client.remove_handler(handler)
                    await new_client.send_message(found_chat_id, "✅ **Database Connected Successfully!**")
                    await save_and_finish(new_client, user_id, session["token"], found_chat_id, msg)

                except asyncio.TimeoutError:
                    new_client.remove_handler(handler)
                    await new_client.stop()
                    await msg.edit("❌ **Timeout:** I didn't receive a message from the channel.\nPlease try `/clone` again.")
                except Exception as e2:
                    await new_client.stop()
                    await msg.edit(f"❌ **Error:** {e2}")

        except Exception as e:
            if user_id in CLONE_SESSION: del CLONE_SESSION[user_id]
            await msg.edit(f"❌ **System Error:** {e}")

async def save_and_finish(client, user_id, token, channel_id, msg_obj):
    # Update running client config
    client.log_channel = channel_id
    
    # Save to DB
    await clones_col.insert_one({
        "token": token, 
        "user_id": user_id, 
        "username": client.me.username,
        "log_channel": channel_id
    })
    
    if user_id in CLONE_SESSION: del CLONE_SESSION[user_id]
    
    await msg_obj.edit(
        f"🎉 **Bot Created Successfully!**\n\n"
        f"🤖 **Bot:** @{client.me.username}\n"
        f"📢 **DB Channel:** `{channel_id}`\n\n"
        "You can now use your own bot to store files!"
    )

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
