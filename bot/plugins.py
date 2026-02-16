from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from bot.fsub import get_fsub_status
from bot.clone import start_clone_bot, clones_col, RUNNING_CLONES
from bot.tinyurl_helper import shorten_url
from bot.admin_ui import admin_panel
from bot.clone_ui import clone_dashboard
import secrets, datetime

# DUAL DB SETUP
main_client = AsyncIOMotorClient(Config.MONGO_URL)
main_db = main_client.TelegramBotCluster
users_col = main_db.large_file_users
main_files_col = main_db.large_files
clones_col = main_db.clones

clone_client = AsyncIOMotorClient(Config.CLONE_MONGO_URL)
clone_db = clone_client.CloneBotCluster
clone_files_col = clone_db.large_files 

user_states = {}
temp_tokens = {}
password_states = {}

DEFAULT_PIC = getattr(Config, 'BOT_PIC', "https://i.imgur.com/8Qj8X9L.jpeg")

async def is_premium(user_id):
    user = await users_col.find_one({"_id": user_id})
    if user and user.get("plan_type") == "premium":
        if user.get("plan_expiry") and user["plan_expiry"] > datetime.datetime.now(): return True
        else: await users_col.update_one({"_id": user_id}, {"$set": {"plan_type": "free"}})
    return False

async def check_limits(user_id, type):
    user = await users_col.find_one({"_id": user_id})
    today = datetime.datetime.now().date().isoformat()
    usage = user.get("usage", {})
    if usage.get("date") != today: usage = {"date": today, "files": 0, "expiry": 0}
    
    if type == 'files':
        if usage["files"] >= Config.FREE_DAILY_LIMIT: return False
        usage["files"] += 1
    elif type == 'expiry':
        if usage["expiry"] >= Config.FREE_EXPIRY_LIMIT: return False
        usage["expiry"] += 1
    
    await users_col.update_one({"_id": user_id}, {"$set": {"usage": usage}})
    return True

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    uid = message.from_user.id
    if uid == Config.OWNER_ID: return await admin_panel(client, message)

    user = await users_col.find_one({"_id": uid})
    if not user:
        # Referral Logic
        if len(message.command) > 1 and message.command[1].startswith("ref_"):
            try:
                ref_id = int(message.command[1].split("_")[1])
                if ref_id != uid:
                    await users_col.update_one({"_id": ref_id}, {"$inc": {"referral_points": Config.REFERRAL_POINTS}})
            except: pass
        await users_col.insert_one({"_id": uid, "plan_type": "free", "referral_points": 0})
        user = await users_col.find_one({"_id": uid})

    is_prem = await is_premium(uid)
    if not is_prem and not await get_fsub_status(client, message): return

    text = f"👋 **Hi {message.from_user.first_name}**\nPlan: `{'PREMIUM' if is_prem else 'FREE'}`\nPoints: `{user.get('referral_points', 0)}`"
    btns = [
        [InlineKeyboardButton("📂 Files", callback_data="my_links"), InlineKeyboardButton("🎁 Refer", callback_data="referral_menu")],
        [InlineKeyboardButton("💎 Upgrade", callback_data="upgrade_plan"), InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")],
        [InlineKeyboardButton("🤖 Create Bot", callback_data="clone_start") if not await clones_col.find_one({"user_id": uid}) else InlineKeyboardButton("🤖 Manage Bot", callback_data="clone_manage")]
    ]
    await message.reply_photo(DEFAULT_PIC, caption=text, reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex("referral_menu"))
async def ref_menu(client, query):
    uid = query.from_user.id
    user = await users_col.find_one({"_id": uid})
    link = f"https://t.me/{client.me.username}?start=ref_{uid}"
    text = f"🎁 **Referral**\nPoints: `{user.get('referral_points')}`\nLink: `{link}`"
    btns = [[InlineKeyboardButton("Redeem 7 Days", callback_data="redeem_7")], [InlineKeyboardButton("Back", callback_data="home")]]
    await query.message.edit_caption(text, reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex(r"redeem_"))
async def redeem(client, query):
    uid = query.from_user.id
    days = 7
    cost = Config.PREMIUM_COST_WEEKLY
    user = await users_col.find_one({"_id": uid})
    if user.get("referral_points", 0) < cost: return await query.answer("❌ Not enough points", show_alert=True)
    
    exp = datetime.datetime.now() + datetime.timedelta(days=days)
    if user.get("plan_type") == "premium": exp = user["plan_expiry"] + datetime.timedelta(days=days)
    
    await users_col.update_one({"_id": uid}, {"$inc": {"referral_points": -cost}, "$set": {"plan_type": "premium", "plan_expiry": exp}})
    await query.answer("✅ Redeemed!", show_alert=True)
    await ref_menu(client, query)

@Client.on_message(filters.command("clone") & filters.private)
async def clone_cmd(client, message):
    user_states[message.from_user.id] = "WAITING_FOR_TOKEN"
    await message.reply_text("🤖 Send Bot Token.")

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "clone"]))
async def conversation(client, message):
    uid = message.from_user.id
    if uid in password_states:
        file_id = password_states[uid]
        await (clone_files_col if client.me.id in RUNNING_CLONES else main_files_col).update_one({"unique_id": file_id}, {"$set": {"password": message.text.strip()}})
        del password_states[uid]
        return await message.reply_text(f"✅ Password Set: `{message.text}`")
        
    state = user_states.get(uid)
    if state == "WAITING_FOR_TOKEN":
        temp_tokens[uid] = message.text.strip()
        user_states[uid] = "WAITING_FOR_CHANNEL"
        await message.reply_text("✅ Send Log Channel ID.")
    elif state == "WAITING_FOR_CHANNEL":
        token = temp_tokens.get(uid)
        bot_info, final_id = await start_clone_bot(token, message.text.strip())
        if bot_info:
            await clones_col.update_one({"user_id": uid}, {"$set": {"token": token, "log_channel": final_id, "bot_id": bot_info.id, "username": bot_info.username}}, upsert=True)
            await message.reply_text(f"✅ Bot Started: @{bot_info.username}")
        del user_states[uid]

@Client.on_callback_query(filters.regex(r"^expiry_menu_"))
async def exp_menu(client, query):
    if not await is_premium(query.from_user.id) and not await check_limits(query.from_user.id, 'expiry'):
        return await query.answer("❌ Daily Limit Reached", show_alert=True)
    id = query.data.split("_")[-1]
    btns = [[InlineKeyboardButton("1 Hour", callback_data=f"set_exp_{id}_3600")], [InlineKeyboardButton("Remove", callback_data=f"set_exp_{id}_0")]]
    await query.message.reply_text("Select Expiry:", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex(r"^set_exp_"))
async def set_exp(client, query):
    _, _, id, sec = query.data.split("_")
    sec = int(sec)
    col = clone_files_col if client.me.id in RUNNING_CLONES else main_files_col
    if sec == 0: await col.update_one({"unique_id": id}, {"$unset": {"expiry_date": ""}})
    else: await col.update_one({"unique_id": id}, {"$set": {"expiry_date": datetime.datetime.now() + datetime.timedelta(seconds=sec)}})
    await query.message.edit_text("✅ Updated.")

@Client.on_callback_query(filters.regex(r"^lock_menu_"))
async def lock_menu(client, query):
    if not await is_premium(query.from_user.id):
        # Simplistic check for total passwords
        if await main_files_col.count_documents({"user_id": query.from_user.id, "password": {"$exists": True}}) >= Config.FREE_PASSWORD_LIMIT:
            return await query.answer("❌ Password Limit Reached", show_alert=True)
    password_states[query.from_user.id] = query.data.split("_")[-1]
    await query.message.reply_text("🔒 Send Password:", reply_markup=ForceReply(True))

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_file(client, message):
    uid = message.from_user.id
    if user_states.get(uid) or password_states.get(uid): return
    is_prem = await is_premium(uid)
    
    if not is_prem:
        if not await get_fsub_status(client, message): return
        if not await check_limits(uid, 'files'): return await message.reply_text("❌ Daily Limit Reached")

    clone_data = RUNNING_CLONES.get(client.me.id)
    target = clone_data['log_channel'] if clone_data else Config.LOG_CHANNEL
    try: log = await message.forward(target)
    except: return await message.reply_text("❌ Forward Error.")

    uid_str = secrets.token_urlsafe(8)
    media = message.document or message.video or message.audio
    doc = {
        "unique_id": uid_str, "user_id": uid, "message_id": log.id, "bot_id": client.me.id,
        "file_name": getattr(media, 'file_name', 'file'), "mime_type": getattr(media, 'mime_type', ''), "file_size": getattr(media, 'file_size', 0)
    }

    if client.me.id in RUNNING_CLONES: await clone_files_col.insert_one(doc)
    else: await main_files_col.insert_one(doc)

    base = Config.BLOGGER_URL if Config.BLOGGER_URL else f"{Config.URL}/watch"
    link = f"{base}?id={uid_str}" if Config.BLOGGER_URL else f"{base}/{uid_str}"
    
    user = await users_col.find_one({"_id": uid})
    if is_prem and user.get("shortener_active"): link = await shorten_url(link) or link

    btns = [[InlineKeyboardButton("🚀 Share", url=f"https://t.me/share/url?url={link}")],
            [InlineKeyboardButton("⏳ Validity", callback_data=f"expiry_menu_{uid_str}"), InlineKeyboardButton("🔒 Lock", callback_data=f"lock_menu_{uid_str}")]]
    await message.reply_text(f"✅ **Secured!**\n🔗 `{link}`", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex("home"))
async def home(c, q): await q.message.delete(); await start_handler(c, q.message)