from pyrogram import Client, filters

@Client.on_message(filters.command("start") & filters.private)
async def clone_start(client, message):
    # Custom interface for clones
    me = await client.get_me()
    await message.reply_text(
        f"👋 **Welcome to {me.mention}!**\n\n"
        "I am a custom file-to-link bot.\n"
        "Just send me a file, and I will generate a fast download link for you."
    )