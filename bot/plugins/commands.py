import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply
from pyrogram.handlers import MessageHandler
from bot.clone import start_clone, db
from config import Config

CLONE_SESSION = {}

@Client.on_message(filters.command("clone") & filters.private)
async def clone_init(client, message):
    user_id = message.from_user.id
    CLONE_SESSION[user_id] = {"step": "WAIT_TOKEN"}
    await message.reply_text("🤖 **Clone Bot Wizard**\nSend Bot Token.", reply_markup=ForceReply(selective=True, placeholder="Token..."))

@Client.on_message(filters.private & (filters.text | filters.forwarded) & ~filters.command(["start", "clone"]))
async def clone_wizard_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in CLONE_SESSION: return 
    session = CLONE_SESSION[user_id]
    text = message.text.strip() if message.text else ""
    if text == "/cancel":
        del CLONE_SESSION[user_id]
        return await message.reply("Cancelled.")

    if session["step"] == "WAIT_TOKEN":
        session["token"] = text
        session["step"] = "WAIT_CHANNEL"
        await message.reply_text("✅ **Token Accepted!**\nNow create a Private Channel, add your bot as admin, and **Forward a message** from it here.")

    elif session["step"] == "WAIT_CHANNEL":
        channel_id = message.forward_from_chat.id if message.forward_from_chat else None
        if not channel_id: return await message.reply("❌ Forward a message from the channel.")
        
        msg = await message.reply("⚙️ Setting up...")
        try:
            new_client, err = await start_clone(session["token"], user_id, 0)
            if not new_client: return await msg.edit(f"❌ Error: {err}")
            
            # Save
            new_client.log_channel = channel_id
            await db.clones.insert_one({"token": session["token"], "user_id": user_id, "username": new_client.me.username, "log_channel": channel_id})
            del CLONE_SESSION[user_id]
            await msg.edit(f"✅ **Success!** Bot: @{new_client.me.username}")
        except Exception as e:
            await msg.edit(f"❌ Error: {e}")
