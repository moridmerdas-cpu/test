import os
import sqlite3
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========= تنظیمات =========
TOKEN = os.environ.get("BOT_TOKEN")
ADMINS = [601668306, 8588773170]  # آیدی عددی ادمین‌ها
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") + WEBHOOK_PATH

# ========= دیتابیس =========
db = sqlite3.connect("db.sqlite", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    source INTEGER,
    target INTEGER,
    active INTEGER
)
""")
db.commit()

def is_admin(user_id):
    return user_id in ADMINS

def get_settings():
    cur.execute("SELECT source, target, active FROM settings WHERE id=1")
    row = cur.fetchone()
    return row if row else (None, None, 0)

def save_settings(source=None, target=None, active=None):
    s, t, a = get_settings()
    cur.execute("""
    INSERT OR REPLACE INTO settings (id, source, target, active)
    VALUES (1, ?, ?, ?)
    """, (
        source if source is not None else s,
        target if target is not None else t,
        active if active is not None else a
    ))
    db.commit()

# ========= پنل =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    keyboard = [
        [
            InlineKeyboardButton("📥 تنظیم گروه", callback_data="set_group"),
            InlineKeyboardButton("📤 تنظیم چنل", callback_data="set_channel")
        ],
        [
            InlineKeyboardButton("▶️ شروع فورواد", callback_data="start_fw"),
            InlineKeyboardButton("⏹ توقف فورواد", callback_data="stop_fw")
        ]
    ]

    await update.message.reply_text(
        "🎛 پنل مدیریت ربات",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_admin(q.from_user.id):
        return

    if q.data == "set_group":
        context.user_data["mode"] = "set_group"
        await q.edit_message_text("📥 یوزرنیم گروه را بفرست (مثال: @mygroup)")

    elif q.data == "set_channel":
        context.user_data["mode"] = "set_channel"
        await q.edit_message_text("📤 یوزرنیم چنل را بفرست (مثال: @mychannel)")

    elif q.data == "start_fw":
        save_settings(active=1)
        await q.edit_message_text("✅ فورواد فعال شد")

    elif q.data == "stop_fw":
        save_settings(active=0)
        await q.edit_message_text("⛔ فورواد متوقف شد")

async def capture_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return
    if not is_admin(update.effective_user.id):
        return

    mode = context.user_data.get("mode")
    if not mode:
        return

    text = update.message.text.strip()
    if not text.startswith("@"):
        await update.message.reply_text("❌ یوزرنیم باید با @ باشد")
        return

    try:
        chat = await context.bot.get_chat(text)
    except:
        await update.message.reply_text("❌ پیدا نشد یا دسترسی ندارم")
        return

    if mode == "set_group" and chat.type in ["group", "supergroup"]:
        save_settings(source=chat.id)
        context.user_data["mode"] = None
        await update.message.reply_text(f"✅ گروه «{chat.title}» وصل شد")

    elif mode == "set_channel" and chat.type == "channel":
        save_settings(target=chat.id)
        context.user_data["mode"] = None
        await update.message.reply_text(f"✅ چنل «{chat.title}» وصل شد")

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source, target, active = get_settings()
    if not active or not update.message:
        return
    if update.message.chat_id == source:
        await update.message.forward(chat_id=target)

# ========= FastAPI =========
app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(buttons))
tg_app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, capture_username))
tg_app.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, forward))

@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
