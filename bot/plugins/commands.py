import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from pyrogram.handlers import MessageHandler
from bot.clone import start_clone, db
from config import Config

CLONE_SESSION = {}

def parse_channel_input(message: Message):
    text = message.text.strip() if message.text else ""
    if message.forward_from_chat: return message.forward_from_chat.id
    if re.match(r"^-100\d+$", text): return int(text)
    private_link_match = re.search(r"t\.me\/c\/(\d+)", text)
    if private_link_match: return int(f"-100{private_link_match.group(1)}")
    username_match = re.search(r"(?:t\.me\/|@)(\w{5,32})", text)
    if username_match:
        name = username_match.group(1)
        if name != "c": return f"@{name}"
    return None

@Client.on_message(filters.command("clone") & filters.private)
async def clone_init(client, message):
    user_id = message.from_user.id
    CLONE_SESSION[user_id] = {"step": "WAIT_TOKEN"}
    await message.reply_text("🤖 **Clone Bot Wizard**\n\nSend your **Bot Token** from @BotFather.\n_(Send /cancel to stop)_", reply_markup=ForceReply(selective=True, placeholder="12345:ABC..."))

@Client.on_message(filters.private & (filters.text | filters.forwarded) & ~filters.command(["start", "clone"]))
async def clone_wizard_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in CLONE_SESSION: return 
    
    session = CLONE_SESSION[user_id]
    text = message.text.strip() if message.text else ""

    if text.lower() == "/cancel":
        del CLONE_SESSION[user_id]
        return await message.reply("🚫 **Cancelled.**")

    if session["step"] == "WAIT_TOKEN":
        if not re.match(r"\d+:[\w-]{35}", text): return await message.reply("❌ **Invalid Token.**")
        session["token"] = text
        session["step"] = "WAIT_CHANNEL"
        await message.reply_text("✅ **Token Accepted!**\n\n1. Create a **Private Channel**.\n2. Add your new bot as **Admin**.\n3. **Forward a Message** from that channel here.", reply_markup=ForceReply(selective=True, placeholder="Forward message..."))

    elif session["step"] == "WAIT_CHANNEL":
        channel_id = parse_channel_input(message)
        if not channel_id: return await message.reply("❌ **Invalid Channel.** Forward a message from the channel.")
        
        msg = await message.reply("⚙️ **Starting Bot...**")
        try:
            new_client, error_msg = await start_clone(session["token"], user_id, 0)
            if not new_client: return await msg.edit(f"❌ **Error:** `{error_msg}`")

            await msg.edit("⚙️ **Verifying Channel...**")
            try:
                chat_info = await new_client.get_chat(channel_id)
                final_channel_id = chat_info.id
                await new_client.send_message(final_channel_id, "✅ **Database Connected!**")
                await save_and_finish(new_client, user_id, session["token"], final_channel_id, msg)
            except Exception:
                await msg.edit("⚠️ **I can't see the channel.**\n\n👉 **Send a message in your channel NOW.**\nI am listening...")
                future = asyncio.get_running_loop().create_future()
                async def discovery_handler(c, m):
                    if m.chat.id == channel_id or (m.forward_from_chat and m.forward_from_chat.id == channel_id):
                        if not future.done(): future.set_result(m.chat.id)
                
                handler = MessageHandler(discovery_handler)
                new_client.add_handler(handler)
                try:
                    found_chat_id = await asyncio.wait_for(future, timeout=60.0)
                    new_client.remove_handler(handler)
                    await new_client.send_message(found_chat_id, "✅ **Connected!**")
                    await save_and_finish(new_client, user_id, session["token"], found_chat_id, msg)
                except:
                    await new_client.stop()
                    await msg.edit("❌ **Timeout.** I couldn't connect.")
        except Exception as e:
            if user_id in CLONE_SESSION: del CLONE_SESSION[user_id]
            await msg.edit(f"❌ **Error:** {e}")

async def save_and_finish(client, user_id, token, channel_id, msg_obj):
    client.log_channel = channel_id
    # Updated: Using db.clones directly
    await db.clones.insert_one({
        "token": token, 
        "user_id": user_id, 
        "username": client.me.username, 
        "log_channel": channel_id
    })
    if user_id in CLONE_SESSION: del CLONE_SESSION[user_id]
    await msg_obj.edit(f"🎉 **Success!**\n🤖 @{client.me.username}\n📢 Channel: `{channel_id}`")
