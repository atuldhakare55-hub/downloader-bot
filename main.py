import os
import time
import asyncio
import sqlite3
import aiohttp
from aiohttp import web

# Python 3.14 loop fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant

API_ID = 37940634
API_HASH = "6c9bf207b1eba747bb4ae29d8b8fa8e8"
BOT_TOKEN = "9028661518:AAEnoagL3xyE0VYq_ykXg_gpisvzmvQxYtk"
ADMIN_USERNAME = "Akdgak"

conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        referrals INTEGER DEFAULT 0,
        premium_until INTEGER DEFAULT 0,
        token_pass_until INTEGER DEFAULT 0
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        admin_id INTEGER DEFAULT 0,
        s1_site TEXT,
        s1_api TEXT,
        s2_site TEXT,
        s2_api TEXT,
        fsub_ch1 INTEGER DEFAULT 0,
        fsub_ch2 INTEGER DEFAULT 0,
        fsub_link1 TEXT DEFAULT 'https://t.me/',
        fsub_link2 TEXT DEFAULT 'https://t.me/'
    )
''')
conn.commit()

cursor.execute("SELECT * FROM settings WHERE id = 1")
if not cursor.fetchone():
    cursor.execute("""
        INSERT INTO settings 
        (id, admin_id, s1_site, s1_api, s2_site, s2_api, fsub_ch1, fsub_ch2, fsub_link1, fsub_link2) 
        VALUES (1, 0, 'droplink.co', 'your_api_1', 'shorturllink.in', 'your_api_2', 0, 0, 'https://t.me/', 'https://t.me/')
    """)
    conn.commit()

app = Client("terabox_pro_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def get_user(user_id):
    cursor.execute("SELECT referrals, premium_until, token_pass_until FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def get_settings():
    cursor.execute("SELECT admin_id, s1_site, s1_api, s2_site, s2_api, fsub_ch1, fsub_ch2, fsub_link1, fsub_link2 FROM settings WHERE id = 1")
    return cursor.fetchone()

def is_admin(user):
    sett = get_settings()
    stored_admin_id = sett[0]
    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        if stored_admin_id != user.id:
            cursor.execute("UPDATE settings SET admin_id = ? WHERE id = 1", (user.id,))
            conn.commit()
        return True
    return user.id == stored_admin_id

async def is_subscribed(client, user_id):
    sett = get_settings()
    ch1, ch2 = sett[5], sett[6]
    for ch_id in [ch1, ch2]:
        if ch_id != 0:
            try:
                await client.get_chat_member(ch_id, user_id)
            except UserNotParticipant:
                return False
            except Exception:
                pass
    return True

async def shorten_url(url, site, api_key):
    api_endpoint = f"https://{site}/api?api={api_key}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, timeout=10) as resp:
                data = await resp.json()
                return data.get("shortenedUrl", url)
    except Exception:
        return url

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    if message.from_user.username and message.from_user.username.lower() == ADMIN_USERNAME.lower():
        cursor.execute("UPDATE settings SET admin_id = ? WHERE id = 1", (user_id,))
        conn.commit()

    user = get_user(user_id)
    text_parts = message.text.split()
    
    if not user:
        referred_by = None
        if len(text_parts) > 1 and text_parts[1].startswith("ref_"):
            try:
                r_id = int(text_parts[1].split("_")[1])
                if r_id != user_id:
                    referred_by = r_id
            except Exception:
                pass

        cursor.execute("INSERT INTO users (user_id, referrals, premium_until, token_pass_until) VALUES (?, 0, 0, 0)", (user_id,))
        conn.commit()

        if referred_by:
            ref_data = get_user(referred_by)
            if ref_data:
                new_refs = ref_data[0] + 1
                prem_until = ref_data[1]
                if new_refs % 2 == 0:
                    prem_until = max(int(time.time()), prem_until) + 86400
                    try:
                        await client.send_message(referred_by, "🎉 Badhai ho! 2 referrals poore hone par 24h VIP Premium mil gaya!")
                    except Exception:
                        pass
                cursor.execute("UPDATE users SET referrals = ?, premium_until = ? WHERE user_id = ?", (new_refs, prem_until, referred_by))
                conn.commit()

    subbed = await is_subscribed(client, user_id)
    sett = get_settings()
    if not subbed:
        buttons = []
        if sett[5] != 0:
            buttons.append([InlineKeyboardButton("📢 Channel 1", url=sett[7])])
        if sett[6] != 0:
            buttons.append([InlineKeyboardButton("📢 Channel 2", url=sett[8])])
        buttons.append([InlineKeyboardButton("🔄 Verify Join", url=f"https://t.me/{(await client.get_me()).username}?start=check")])
        return await message.reply_text("⚠️ Bot use karne ke liye channels join karein:", reply_markup=InlineKeyboardMarkup(buttons))

    if len(text_parts) > 1 and text_parts[1].startswith("verify2_"):
        cursor.execute("UPDATE users SET token_pass_until = ? WHERE user_id = ?", (int(time.time()) + 86400, user_id))
        conn.commit()
        return await message.reply_text("✅ Verification successful! 24 ghante ka pass active ho gaya.")

    bot_uname = (await client.get_me()).username
    ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"
    
    welcome_text = (
        f"👋 Namaste {message.from_user.first_name}!\n\n"
        "Terabox video link bhejo download ke liye.\n\n"
        f"🔗 Referral Link: `{ref_link}`\n"
        "👉 2 referrals = 1 din VIP Premium Free!"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy VIP Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")]
    ])
    await message.reply_text(welcome_text, reply_markup=kb)

@app.on_callback_query()
async def cb_handler(client, query):
    user_id = query.from_user.id
    user = get_user(user_id) or (0, 0, 0)
    if query.data == "my_status":
        prem_until = user[1]
        now = int(time.time())
        status = f"✅ Active ({int((prem_until - now)/3600)}h)" if prem_until > now else "❌ Inactive"
        await query.message.edit_text(f"👤 User ID: `{user_id}`\n👥 Referrals: `{user[0]}`\n💎 Premium: {status}")
    elif query.data == "buy_premium":
        await query.message.edit_text(f"💎 Premium lene ke liye contact karein: @{ADMIN_USERNAME}")

@app.on_message(filters.regex(r"https?://[^\s]+") & filters.private)
async def process_video(client, message):
    user_id = message.from_user.id
    if not (await is_subscribed(client, user_id)):
        return await message.reply_text("⚠️ Pehle channels join karein.")

    user = get_user(user_id) or (0, 0, 0)
    now = int(time.time())
    is_prem = user[1] > now
    token_valid = user[2] > now

    if not is_prem and not token_valid:
        sett = get_settings()
        s1_site, s1_api, s2_site, s2_api = sett[1], sett[2], sett[3], sett[4]
        bot_uname = (await client.get_me()).username
        step2_link = f"https://t.me/{bot_uname}?start=verify2_{user_id}"
        s2_short = await shorten_url(step2_link, s2_site, s2_api)
        final_short = await shorten_url(s2_short, s1_site, s1_api)

        btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔓 24h Access Unlock Karein", url=final_short)]])
        return await message.reply_text("⚠️ Download karne ke liye link verify karein:", reply_markup=btn)

    status = await message.reply_text("🔄 Processing link...")
    url = message.text.strip()
    try:
        api_url = f"https://terabox-api.graydeveloper.com/api?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as resp:
                data = await resp.json()
                if data and ("direct_link" in str(data) or "download_link" in str(data)):
                    dl = data.get("direct_link") or data.get("download_link")
                    title = data.get("title", "Terabox Video")
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Direct Download", url=dl)]])
                    await status.delete()
                    await message.reply_text(f"🎬 `{title}`", reply_markup=kb)
                else:
                    await status.edit_text("❌ Direct link fetch nahi hua.")
    except Exception as e:
        await status.edit_text(f"⚠️ Error: `{str(e)}`")

@app.on_message(filters.command("admin") & filters.private)
async def admin_ctrl(client, message):
    if not is_admin(message.from_user): return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    sett = get_settings()
    await message.reply_text(
        f"⚙️ Admin Panel\n\nUsers: `{total_users}`\nShortener 1: `{sett[1]}`\nShortener 2: `{sett[3]}`\n\nCommands: `/set_s1`, `/set_s2`, `/set_ch1`, `/set_ch2`, `/add_prem`, `/broadcast`"
    )

# Render dummy web server (Port timeout fix)
async def handle_ping(request):
    return web.Response(text="Bot is running fine!")

async def start_web_server():
    server = web.Application()
    server.router.add_get("/", handle_ping)
    runner = web.AppRunner(server)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await app.start()
    print("Bot is Started Successfully!")
    from pyrogram import idle
    await idle()
    await app.stop()

if __name__ == "__main__":
        loop.run_until_complete(main())
    
