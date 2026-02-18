from pyrogram import Client, filters
from config import Config

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_conversion(client, message):
    # 1. Forward to Log Channel
    log_msg = await message.forward(Config.LOG_CHANNEL)
    
    # 2. Generate the Direct Link using your Render URL
    # Replace 'your-app-name' with your actual Render service name
    render_url = "https://your-app-name.onrender.com" 
    direct_link = f"{render_url}/download/{log_msg.id}"
    
    await message.reply_text(
        f"🚀 **Direct Download Link Generated!**\n\n"
        f"🔗 `{direct_link}`\n\n"
        f"This link works directly in your browser or IDM.",
        disable_web_page_preview=True
    )
