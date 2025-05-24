import re    
import os 
import sys
import time      
import pymongo
import asyncio
import tgcrypto
import requests
import datetime
import random
from pyromod import listen
from pyrogram import enums 
from Crypto.Cipher import AES
from pymongo import MongoClient
from aiohttp import ClientSession    
from pyrogram.types import Message, BotCommand  
from pyrogram import Client, filters
from base64 import b64encode, b64decode
from pyrogram.errors import FloodWait, PeerIdInvalid, RPCError
from pyrogram.types import User, Message        
from pyrogram.types.messages_and_media import message
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URI, OWNER_ID
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid

#========================= Initaited bot ===========================
# Initialize bot and MongoDB
app = Client("forward_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo["forward_bot"]
users = db["users"]
cancel_flags = {}

#======================= Set bot commands ========================
@app.on_message(filters.command("set") & filters.user(OWNER_ID))
async def set_bot_commands(client, message):
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("target", "🎯 Set target channel"),
        BotCommand("filters", "🔍 Toggle media filters"),
        BotCommand("cancel", "🛑 Cancel forwarding"),
        BotCommand("targetinfo", "ℹ️ Show current target"),
        BotCommand("forward", "📤 Forward messages"),
        BotCommand("reset", "♻️ Reset filters & target"),
    ]

    await client.set_bot_commands(commands)
    await message.reply("<blockquote>✅ Bot commands set successfully.</blockquote>")

#===================== Detect chat id from message link ===================
# Utility to extract chat_id and message_id from a message link
def extract_ids_from_link(link):
    match = re.search(r"https://t.me/(c/)?([\w_]+)/?(\d+)?", link)
    if not match:
        return None, None
    if match.group(1):  # private group/channel
        chat_id = int(f"-100{match.group(2)}")
    else:
        username = match.group(2)
        chat_id = username if not username.isdigit() else int(username)
    msg_id = int(match.group(3)) if match.group(3) else None
    return chat_id, msg_id

#================================ Start command to start bot ============================
image_list = [
    "https://www.pixelstalk.net/wp-content/uploads/2025/03/A-breathtaking-image-of-a-lion-roaring-proudly-atop-a-rocky-outcrop-with-dramatic-clouds-and-rays-of-sunlight-breaking-through-2.webp"
    ]
class Data:
    START = (
        "🌟 𝐇𝐞𝐲  {0} , 𝐖𝐄𝐋𝐂𝐎𝐌𝐄  !\n\n"
    )
# Define the start command handler
@app.on_message(filters.command("start"))
async def start(client: Client, msg: Message):
    user = await client.get_me()
    mention = user.mention
    random_image = random.choice(image_list)
    start_message = await client.send_photo(
         chat_id=msg.chat.id,
         photo=random_image,
         caption=Data.START.format(msg.from_user.mention)
    )
    await asyncio.sleep(1)
    await start_message.edit_text(
        Data.START.format(msg.from_user.mention) +
        "<blockquote>👋 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐅𝐎𝐑𝐖𝐀𝐑𝐃 𝐁𝐎𝐓 👋</blockquote>\n\n"
        "<blockquote>📚 **Available Commands For This Bot**</blockquote>\n\n"
        "• /target – Set target via message link\n\n"
        "• /forward – Forward messages\n\n"
        "• /cancel – Cancel ongoing forwarding\n\n"
        "• /filters – Edit caption in forwarding\n\n"
        "• /reset – Reset settings\n\n"
        "• /targetinfo –Information about target\n\n"
        "<blockquote>🚀 **Use the bot to forward messages fast and easily!**</blockquote>\n",
        reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin", url="https://t.me/Thebhumihar")]
        ])
    )
#================================ Set filters =============================
@app.on_message(filters.command("filters") & filters.private)
async def set_filters(client, message):
    user_id = message.from_user.id
    # Ensure fields exist
    users.update_one({"user_id": user_id}, {
        "$setOnInsert": {
            "filters": {"replace": {}, "delete": []},
            "auto_pin": False
        }
    }, upsert=True)

    user = users.find_one({"user_id": user_id})
    filters_data = user.get("filters", {})
    replace = filters_data.get("replace", {})
    delete = filters_data.get("delete", [])
    auto_pin = filters_data.get("auto_pin", False)

    await message.reply(
        "<blockquote>**🔧 Current Filters :**</blockquote>\n\n"
        f"🔁 Replace: `{replace}`\n"
        f"❌ Delete: `{delete}`\n"
        f"📌 Auto Pin: `{auto_pin}`\n\n"
        "<blockquote>**Send filters in one of these formats :**</blockquote>\n\n"
        "`word1 => word2` to replace\n"
        "`delete: word` to delete word\n"
        "`auto_pin: true/false` to toggle auto pinning\n\n"
        "Type /done to finish."
    )

    while True:
        try:
            response = await client.listen(message.chat.id, timeout=120)
        except asyncio.TimeoutError:
            return await message.reply("<blockquote>⏳ Timed out. Run /filters again.</blockquote>")
        
        text = response.text.strip()

        if text.lower() == "/done":
            return await message.reply("<blockquote>✅ Filters updated !</blockquote>")

        if "=>" in text:
            try:
                old, new = [t.strip() for t in text.split("=>", 1)]
                replace[old] = new
                users.update_one({"user_id": user_id}, {"$set": {"filters.replace": replace}})
                await message.reply(f"🔁 Added replace: `{old}` => `{new}`")
            except Exception:
                await message.reply("<blockquote>❌ Invalid replace format. Use: `old => new`</blockquote>")

        elif text.lower().startswith("delete:"):
            word = text.split("delete:", 1)[1].strip()
            if word not in delete:
                delete.append(word)
                users.update_one({"user_id": user_id}, {"$set": {"filters.delete": delete}})
            await message.reply(f"❌ Will delete: `{word}`")

        elif text.lower().startswith("auto_pin:"):
            val_raw = text.split("auto_pin:", 1)[1].strip().lower()
            val = val_raw in ["true", "yes", "1"]
            users.update_one({"user_id": user_id}, {"$set": {"filters.auto_pin": val}})
            await message.reply(f"📌 Auto pin set to: `{val}`")

        else:
            await message.reply("<blockquote>❌ Invalid format. Try again or type /done to finish.</blockquote>")

#============================= Reset filters ====================================
@app.on_message(filters.command("reset") & filters.private)
async def reset_selected_settings(client, message):
    user_id = message.from_user.id
    users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "target_chat": None,
                "filters.replace": {},
                "filters.delete": [],
                "auto_pin": False
            }
        },
        upsert=True
    )

    await message.reply(
        "<blockquote>♻️ <b>Settings Reset Successfully:</b></blockquote>\n\n"
        "• 🎯 Target Channel  :  Cleared\n"
        "• 🔁 Replace Words  :  Cleared\n"
        "• ❌ Delete Words  :  Cleared\n"
        "• 📌 Auto Pin  :  Disabled"
    )
#=============================== Set target chat ==================================
@app.on_message(filters.command("target") & filters.private)
async def set_target(client, message):
    user_id = message.from_user.id
    await message.reply("<blockquote>📩 Send a **message link** from the **target channel**</blockquote>")
    try:
        link_msg = await client.listen(message.chat.id, timeout=120)
        link = link_msg.text.strip()
        chat_id, _ = extract_ids_from_link(link)
        if not chat_id:
            return await message.reply("<blockquote>❌ Invalid link</blockquote>")
        users.update_one({"user_id": message.from_user.id}, {"$set": {"target_chat": chat_id}}, upsert=True)
        await message.reply(f"<blockquote>✅ Target set to `{chat_id}`</blockquote>")
    except asyncio.TimeoutError:
        await message.reply("<blockquote>⏰ Timed out. Please try again</blockquote>")
        
#================================ Information of target chat =========================
@app.on_message(filters.command("targetinfo") & filters.private)
async def target_info(client, message):
    user_id = message.from_user.id
    user = users.find_one({"user_id": user_id})
    target_chat_id = user.get("target_chat") if user else None

    if not target_chat_id:
        return await message.reply("<blockquote>❌ No target is currently set. Use /target to set one.</blockquote>")

    try:
        chat = await client.get_chat(target_chat_id)
        await message.reply(
            f"<blockquote>🎯 Current Target :</blockquote>\n\n"
            f"• Title : <b>{chat.title}</b>\n"
            f"• ID : <code>{target_chat_id}</code>"
        )
    except Exception:
        await message.reply(
            f"🎯 Current Target ID : <code>{target_chat_id}</code>\n\n"
            f"(⚠️ Bot may not have access to retrieve the title)"
        )
#========================= Start forward ==============================
@app.on_message(filters.command("forward") & filters.private)
async def forward_command(client, message):
    user_id = message.from_user.id
    cancel_flags[user_id] = False

    user = users.find_one({"user_id": user_id})
    target_chat = user.get("target_chat") if user else None
    if not target_chat:
        return await message.reply("<blockquote>❌ No target is set. Use /target to set one.</blockquote>")

    await message.reply("<blockquote>📩 Send the **start message link** from the source channel</blockquote>")
    try:
        start_msg = await client.listen(message.chat.id, timeout=120)
        start_chat, start_id = extract_ids_from_link(start_msg.text.strip())
        if not start_chat or not start_id:
            return await message.reply("<blockquote>❌ Invalid start message link</blockquote>")

        await message.reply("<blockquote>📩 Send the **end message link**</blockquote>")
        end_msg = await client.listen(message.chat.id, timeout=120)
        _, end_id = extract_ids_from_link(end_msg.text.strip())
        if not end_id:
            return await message.reply("<blockquote>❌ Invalid end message link</blockquote>")

    except asyncio.TimeoutError:
        return await message.reply("<blockquote>⏰ Timed out. Please try again</blockquote>")

    total = end_id - start_id + 1
    count = 0
    failed = 0
    start_time = time.time()

    try:
        source_chat = await client.get_chat(start_chat)
        target = await client.get_chat(target_chat)
    except PeerIdInvalid:
        return await message.reply("<blockquote>❌ Bot doesn't have access. Add it to both source and target</blockquote>")

    status = await message.reply(
        f"╔════ 𝐅𝐎𝐑𝐖𝐀𝐑𝐃𝐈𝐍𝐆 𝐈𝐍𝐈𝐓𝐈𝐀𝐓𝐄𝐃 ════╗\n"
        f"┃\n"
        f"┃ 🗂 Source : `{source_chat.title}`\n"
        f"┃ 📤 Target : `{target.title}`\n"
        f"╚══════════════════════════╝"
    )


    for msg_id in range(start_id, end_id + 1):
        if cancel_flags.get(user_id):
            await status.edit(
                f"╔═══ 𝐅𝐎𝐑𝐖𝐀𝐑𝐃𝐈𝐍𝐆 𝐂𝐀𝐍𝐂𝐄𝐋𝐋𝐄𝐃 ═══╗\n"
                f"┃\n"
                f"┃ 📌 Stopped at Message ID: `{msg_id}`\n"
                f"┃ 📤 Messages Forwarded: `{count}` out of `{total}`\n"
                f"╚═════════════════════════╝\n\n"
            )
            cancel_flags[user_id] = False
            return

        try:
            msg = await client.get_messages(start_chat, msg_id)
            if msg and not getattr(msg, "empty", False) and not getattr(msg, "protected_content", False):
                caption = msg.caption
                user_data = users.find_one({"user_id": user_id})
                filters_data = user_data.get("filters", {})
                auto_pin = filters_data.get("auto_pin", False)

                if caption:
                    for old, new in filters_data.get("replace", {}).items():
                        caption = caption.replace(old, new)

                    for word in filters_data.get("delete", []):
                        caption = caption.replace(word, "")

                copied = await msg.copy(
                    target_chat,
                    caption=caption if caption else None,
                    caption_entities=msg.caption_entities if caption else None
                )
                if auto_pin:
                    try:
                        pinned_msg_id = None
                        source_chat = await client.get_chat(msg.chat.id)
                        if source_chat.pinned_message:
                            pinned_msg_id = source_chat.pinned_message.id
                        if pinned_msg_id == msg.id:
                            await asyncio.sleep(1)
                            await client.pin_chat_message(target_chat, copied.id)
                            await asyncio.sleep(0.5)
                            try:
                                await client.delete_messages(target_chat, copied.id + 1)
                            except:
                                pass
                    except Exception as e:
                        print(f"[AutoPin Error] {e}")
                count += 1
            else:
                failed += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            continue
        except RPCError:
            failed += 1
            continue
                
        elapsed = time.time() - start_time
        percent = (count + failed) / total * 100
        eta_seconds = (elapsed / (count + failed)) * (total - count - failed) if (count + failed) else 0
        
        def format_eta(seconds):
            delta = datetime.timedelta(seconds=int(seconds))
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            parts = []
            if days > 0: parts.append(f"{days}d")
            if hours > 0: parts.append(f"{hours}h")
            if minutes > 0: parts.append(f"{minutes}m")
            if secs > 0 or not parts: parts.append(f"{secs}s")
            return " ".join(parts)
        
        eta = format_eta(eta_seconds)
        remaining = total - (count + failed)
        progress_bar = f"{'⚫' * int(percent // 10)}{'⚪' * (10 - int(percent // 10))}"
        elapsed_text = format_eta(int(elapsed))
        
        try:
            await status.edit(
                f"╔══ 🎯 𝐒𝐎𝐔𝐑𝐂𝐄 / 𝐓𝐀𝐑𝐆𝐄𝐓 𝐈𝐍𝐅𝐎 🎯 ══╗\n"
                f"┃\n"
                f"┃ 📤 From  : `{source_chat.title}`\n"
                f"┃ 🎯 To  :  `{target.title}`\n"
                f"╚═════════════════════════╝\n\n"
                f"╔═  📦 𝐅𝐎𝐑𝐖𝐀𝐑𝐃𝐈𝐍𝐆 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 📦  ═╗\n"
                f"┃\n"
                f"┃ 📊 Progress  : `{count + failed}/{total}` ({percent:.2f}%)\n"
                f"┃ 📌 Remaining  : `{remaining}`\n"
                f"┃ ▓ {progress_bar}\n"
                f"╚═════════════════════════╝\n\n"
                f"╔═  📈 𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄 𝐌𝐀𝐓𝐑𝐈𝐂𝐒 📈  ═╗\n"
                f"┃\n"
                f"┃ ✅ Success  : `{count}`\n"
                f"┃ ❌ Deleted  :  `{failed}`\n"
                f"╚═════════════════════════╝\n\n"
                f"╔════ ⏱️ 𝐓𝐈𝐌𝐈𝐍𝐆 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ⏱️ ═════╗\n"
                f"┃\n"
                f"┃ ⌛ Elapsed  : `{elapsed_text}`\n"
                f"┃ ⏳ ETA  :  `{eta}`\n"
                f"╚═════════════════════════╝\n\n"
            )
        except Exception as e:
            print(f"Progress update error: {e}")

        await asyncio.sleep(0.5)

    time_taken = format_eta(time.time() - start_time)
    await status.edit(
        f"╔═  ✅ 𝐅𝐎𝐑𝐖𝐀𝐑𝐃𝐈𝐍𝐆 𝐂𝐎𝐌𝐏𝐋𝐄𝐓𝐄𝐃 ✅  ═╗\n"
        f"┃\n"
        f"┃ 📤 From  : `{source_chat.title}`\n"
        f"┃ 🎯 To  : `{target.title}`\n"
        f"┃ ✅ Success  : `{count}`\n"
        f"┃ ❌ Deleted  : `{failed}`\n"
        f"┃ 📊 Total  : `{total}`\n"
        f"┃ ⏱️ Time  : `{time_taken}`\n"
        f"╚══════════════════════════╝"
    )
#================ Cancel running process ======================
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_forwarding(client, message):
    user_id = message.from_user.id
    cancel_flags[message.from_user.id] = True
    await message.reply(
        f"╔═══ 🛑 𝐂𝐀𝐍𝐂𝐄𝐋 𝐑𝐄𝐐𝐔𝐄𝐒𝐓𝐄𝐃 🛑 ═══╗\n"
        f"┃\n"
        f"┃ ⚙️ Attempting to halt forwarding...\n"
        f"┃ ⏳ Please wait a moment.\n"
        f"╚═════════════════════════╝"
    )
#========= Start bot =============
app.run()
