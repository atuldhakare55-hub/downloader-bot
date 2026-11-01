import asyncio
import os
import sqlite3
import time
import aiohttp

# Python 3.14 / Render ke liye asyncio event loop fix
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ================= Credentials =================
API_ID = 37940634
API_HASH = "6c9bf207b1eba747bb4ae29d8b8fa8e8"
BOT_TOKEN = "9028661518:AAEnoagL3xyE0VYq_ykXg_gpisvzmvQxYtk"
ADMIN_USERNAME = "Akdgak"

# ================= Database Setup =================
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        referrals INTEGER DEFAULT 0,
        premium_until INTEGER DEFAULT 0,
        token_pass_until INTEGER DEFAULT 0
    )
""")
cursor.execute("""
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
""")
conn.commit()

cursor.execute("SELECT * FROM settings WHERE id = 1")
if not cursor.fetchone():
  cursor.execute("""
        INSERT INTO settings 
        (id, admin_id, s1_site, s1_api, s2_site, s2_api, fsub_ch1, fsub_ch2, fsub_link1, fsub_link2) 
        VALUES (1, 0, 'droplink.co', 'your_api_1', 'shorturllink.in', 'your_api_2', 0, 0, 'https://t.me/', 'https://t.me/')
    """)
  conn.commit()

app = Client(
    "terabox_pro_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH
)


# ================= Helpers =================
def get_user(user_id):
  cursor.execute(
      "SELECT referrals, premium_until, token_pass_until FROM users WHERE"
      " user_id = ?",
      (user_id,),
  )
  return cursor.fetchone()


def get_settings():
  cursor.execute(
      "SELECT admin_id, s1_site, s1_api, s2_site, s2_api, fsub_ch1, fsub_ch2,"
      " fsub_link1, fsub_link2 FROM settings WHERE id = 1"
  )
  return cursor.fetchone()


def is_admin(user):
  sett = get_settings()
  stored_admin_id = sett[0]
  if user.username and user.username.lower() == ADMIN_USERNAME.lower():
    if stored_admin_id != user.id:
      cursor.execute(
          "UPDATE settings SET admin_id = ? WHERE id = 1", (user.id,)
      )
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


# ================= Start & Referral =================
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
  user_id = message.from_user.id

  if (
      message.from_user.username
      and message.from_user.username.lower() == ADMIN_USERNAME.lower()
  ):
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

    cursor.execute(
        "INSERT INTO users (user_id, referrals, premium_until,"
        " token_pass_until) VALUES (?, 0, 0, 0)",
        (user_id,),
    )
    conn.commit()

    if referred_by:
      ref_data = get_user(referred_by)
      if ref_data:
        new_refs = ref_data[0] + 1
        prem_until = ref_data[1]

        if new_refs % 2 == 0:
          prem_until = max(int(time.time()), prem_until) + 86400
          try:
            await client.send_message(
                referred_by,
                "🎉 **Badhai ho!** Aapne 2 dosto ko refer kiya hai. Aapko 24"
                " ghante ka VIP premium mil chuka hai!",
            )
          except Exception:
            pass

        cursor.execute(
            "UPDATE users SET referrals = ?, premium_until = ? WHERE user_id ="
            " ?",
            (new_refs, prem_until, referred_by),
        )
        conn.commit()

  subbed = await is_subscribed(client, user_id)
  sett = get_settings()
  if not subbed:
    buttons = []
    if sett[5] != 0:
      buttons.append([InlineKeyboardButton("📢 Channel 1 Join Karein", url=sett[7])])
    if sett[6] != 0:
      buttons.append([InlineKeyboardButton("📢 Channel 2 Join Karein", url=sett[8])])
    buttons.append([
        InlineKeyboardButton(
            "🔄 Join Kar Liya (Check)",
            url=(
                f"https://t.me/{(await client.get_me()).username}?start=check"
            ),
        )
    ])

    return await message.reply_text(
        "⚠️ **Bot ka use karne ke liye pehle channel join karein:**",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

  if len(text_parts) > 1 and text_parts[1].startswith("verify2_"):
    cursor.execute(
        "UPDATE users SET token_pass_until = ? WHERE user_id = ?",
        (int(time.time()) + 86400, user_id),
    )
    conn.commit()
    return await message.reply_text(
        "✅ **Verification successful!**\nAapka 24 ghante ka pass activate ho"
        " gaya hai. Ab link bhejein."
    )

  bot_uname = (await client.get_me()).username
  ref_link = f"https://t.me/{bot_uname}?start=ref_{user_id}"

  welcome_text = (
      f"👋 **Namaste {message.from_user.first_name}!**\n\n"
      "Mujhe koi bhi Terabox video link bhejo, direct download link milega.\n\n"
      f"🔗 **Aapka Referral Link:** `{ref_link}`\n"
      "👉 **2 dosto ko share karein = 1 din ka VIP premium FREE!**"
  )
  kb = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              "💎 VIP Premium Plans", callback_data="buy_premium"
          )
      ],
      [InlineKeyboardButton("📊 Mera Status", callback_data="my_status")],
  ])
  await message.reply_text(welcome_text, reply_markup=kb)


# ================= Buttons =================
@app.on_callback_query()
async def cb_handler(client, query):
  user_id = query.from_user.id
  user = get_user(user_id) or (0, 0, 0)

  if query.data == "my_status":
    prem_until = user[1]
    now = int(time.time())
    status = (
        f"✅ Active ({int((prem_until - now)/3600)} ghante bache)"
        if prem_until > now
        else "❌ Inactive"
    )

    await query.message.edit_text(
        f"👤 **User ID:** `{user_id}`\n👥 **Total Referrals:** `{user[0]}`\n💎"
        f" **Premium Status:** {status}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        ),
    )
  elif query.data == "buy_premium":
    await query.message.edit_text(
        "💎 **VIP Premium Plans:**\n\n• 1 Week = ₹29\n• 1 Month = ₹89\n\n⚡ Direct"
        " 1-click download bina kisi ad ya shortener ke!\n\nBuy karne ke liye"
        f" contact karein: @{ADMIN_USERNAME}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        ),
    )
  elif query.data == "back_home":
    await query.message.delete()


# ================= Terabox Link & 2 Shortener Logic =================
@app.on_message(filters.regex(r"https?://[^\s]+") & filters.private)
async def process_video(client, message):
  user_id = message.from_user.id

  if not (await is_subscribed(client, user_id)):
    return await message.reply_text("⚠️ Pehle upar diye channel join karein.")

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

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔓 24 Ghante Ka Access Unlock Karein", url=final_short
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Ad-free Premium Lein", callback_data="buy_premium"
            )
        ],
    ])
    return await message.reply_text(
        "⚠️ **Download karne ke liye verification zaroori hai:**\n\nNiche diye"
        " link se 2 chhote task paar karein aur 24 ghante ke liye unlimited"
        " download ka maza lein.",
        reply_markup=btn,
    )

  status = await message.reply_text(
      "🔄 **Link process ho raha hai, thoda intezar karein...**"
  )
  url = message.text.strip()

  try:
    api_url = f"https://terabox-api.graydeveloper.com/api?url={url}"
    async with aiohttp.ClientSession() as session:
      async with session.get(api_url, timeout=15) as resp:
        data = await resp.json()
        if data and ("direct_link" in str(data) or "download_link" in str(data)):
          dl = data.get("direct_link") or data.get("download_link")
          title = data.get("title", "Terabox Video")

          kb = InlineKeyboardMarkup(
              [[InlineKeyboardButton("🚀 Direct Download Karein", url=dl)]]
          )
          await status.delete()
          await message.reply_text(
              f"🎬 **File:** `{title}`\n\n✅ Link ready hai:", reply_markup=kb
          )
        else:
          await status.edit_text(
              "❌ Direct link fetch nahi ho saka. Link check karein."
          )
  except Exception as e:
    await status.edit_text(f"⚠️ Error: `{str(e)}`")


# ================= Admin Panel =================
@app.on_message(filters.command("admin") & filters.private)
async def admin_ctrl(client, message):
  if not is_admin(message.from_user):
    return await message.reply_text("❌ Aap admin nahi hain.")

  cursor.execute("SELECT COUNT(*) FROM users")
  total_users = cursor.fetchone()[0]
  sett = get_settings()

  text = (
      "⚙️ **Admin Control Panel**\n\n"
      f"👥 **Total Users:** `{total_users}`\n\n"
      f"🔗 **Shortener 1:** `{sett[1]}` | `{sett[2]}`\n"
      f"🔗 **Shortener 2:** `{sett[3]}` | `{sett[4]}`\n"
      f"📢 **Channel 1:** ID `{sett[5]}` | Link `{sett[7]}`\n"
      f"📢 **Channel 2:** ID `{sett[6]}` | Link `{sett[8]}`\n\n"
      "**Commands:**\n"
      "`/set_s1 site apikey` - Shortener 1 badlein\n"
      "`/set_s2 site apikey` - Shortener 2 badlein\n"
      "`/set_ch1 channel_id link` - Channel 1 set karein\n"
      "`/set_ch2 channel_id link` - Channel 2 set karein\n"
      "`/add_prem user_id days` - Premium dein\n"
      "`/broadcast` - (Kisi message ko reply karke) sabhi ko bhejein"
  )
  await message.reply_text(text)


@app.on_message(filters.command("set_s1") & filters.private)
async def set_s1(client, message):
  if not is_admin(message.from_user):
    return
  try:
    _, site, api_key = message.text.split()
    cursor.execute(
        "UPDATE settings SET s1_site = ?, s1_api = ? WHERE id = 1",
        (site, api_key),
    )
    conn.commit()
    await message.reply_text("✅ Shortener 1 set ho gaya!")
  except Exception:
    await message.reply_text("❌ Format: `/set_s1 droplink.co api_key`")


@app.on_message(filters.command("set_s2") & filters.private)
async def set_s2(client, message):
  if not is_admin(message.from_user):
    return
  try:
    _, site, api_key = message.text.split()
    cursor.execute(
        "UPDATE settings SET s2_site = ?, s2_api = ? WHERE id = 1",
        (site, api_key),
    )
    conn.commit()
    await message.reply_text("✅ Shortener 2 set ho gaya!")
  except Exception:
    await message.reply_text("❌ Format: `/set_s2 shorturllink.in api_key`")


@app.on_message(filters.command("set_ch1") & filters.private)
async def set_ch1(client, message):
  if not is_admin(message.from_user):
    return
  try:
    _, ch_id, link = message.text.split()
    cursor.execute(
        "UPDATE settings SET fsub_ch1 = ?, fsub_link1 = ? WHERE id = 1",
        (int(ch_id), link),
    )
    conn.commit()
    await message.reply_text("✅ Channel 1 set ho gaya!")
  except Exception:
    await message.reply_text(
        "❌ Format: `/set_ch1 -100123456789 https://t.me/yourlink`"
    )


@app.on_message(filters.command("set_ch2") & filters.private)
async def set_ch2(client, message):
  if not is_admin(message.from_user):
    return
  try:
    _, ch_id, link = message.text.split()
    cursor.execute(
        "UPDATE settings SET fsub_ch2 = ?, fsub_link2 = ? WHERE id = 1",
        (int(ch_id), link),
    )
    conn.commit()
    await message.reply_text("✅ Channel 2 set ho gaya!")
  except Exception:
    await message.reply_text(
        "❌ Format: `/set_ch2 -100987654321 https://t.me/yourlink`"
    )


@app.on_message(filters.command("add_prem") & filters.private)
async def add_prem(client, message):
  if not is_admin(message.from_user):
    return
  try:
    _, uid, days = message.text.split()
    uid = int(uid)
    sec = int(days) * 86400
    user = get_user(uid)
    curr = max(int(time.time()), user[1] if user else 0)

    cursor.execute(
        "INSERT INTO users (user_id, referrals, premium_until,"
        " token_pass_until) VALUES (?, 0, ?, 0) ON CONFLICT(user_id) DO UPDATE"
        " SET premium_until = ?",
        (uid, curr + sec, curr + sec),
    )
    conn.commit()
    await message.reply_text(
        f"✅ User `{uid}` ko `{days}` din ka premium de diya gaya."
    )
  except Exception:
    await message.reply_text("❌ Format: `/add_prem 123456789 30`")


@app.on_message(filters.command("broadcast") & filters.private)
async def bcast(client, message):
  if not is_admin(message.from_user):
    return
  if not message.reply_to_message:
    return await message.reply_text(
        "⚠️ Kisi message ko reply karke `/broadcast` likhein."
    )

  cursor.execute("SELECT user_id FROM users")
  users = cursor.fetchall()
  success, failed = 0, 0
  status = await message.reply_text("📢 Broadcast bheja ja raha hai...")

  for u in users:
    try:
      await message.reply_to_message.copy(u[0])
      success += 1
      await asyncio.sleep(0.04)
    except Exception:
      failed += 1

  await status.edit_text(
      f"✅ **Broadcast complete:**\nSuccess: `{success}` | Failed: `{failed}`"
  )


if __name__ == "__main__":
  print("Bot is Starting...")
  app.run()
