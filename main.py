import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

ADMINS = {8321215905}  # آیدی عددی خودت

SETTINGS = {
    "group_username": None,
    "group_id": None,
    "channel_username": None,
    "channel_id": None,
    "forward": False,
}

app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()


# ───── ابزار ─────
def panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن گروه (@)", callback_data="add_group")],
        [InlineKeyboardButton("➕ افزودن چنل (@)", callback_data="add_channel")],
        [
            InlineKeyboardButton("▶️ شروع فوروارد", callback_data="start"),
            InlineKeyboardButton("⏹ توقف فوروارد", callback_data="stop"),
        ],
    ])


def is_admin(uid):
    return uid in ADMINS


# ───── start ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🎛 پنل مدیریت", reply_markup=panel())


# ───── دکمه‌ها ─────
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_admin(q.from_user.id):
        return

    if q.data == "add_group":
        context.user_data["mode"] = "group"
        await q.message.reply_text("👥 یوزرنیم گروه رو بفرست\nمثال: @mygroup")

    elif q.data == "add_channel":
        context.user_data["mode"] = "channel"
        await q.message.reply_text("📢 یوزرنیم چنل رو بفرست\nمثال: @mychannel")

    elif q.data == "start":
        if SETTINGS["group_id"] and SETTINGS["channel_id"]:
            SETTINGS["forward"] = True
            await q.message.reply_text("✅ فوروارد فعال شد")
        else:
            await q.message.reply_text("❌ گروه یا چنل تنظیم نشده")

    elif q.data == "stop":
        SETTINGS["forward"] = False
        await q.message.reply_text("⏹ فوروارد متوقف شد")


# ───── دریافت @username ─────
async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    mode = context.user_data.get("mode")
    if not mode:
        return

    username = update.message.text.strip()
    if not username.startswith("@"):
        await update.message.reply_text("❌ باید با @ شروع بشه")
        return

    try:
        chat = await context.bot.get_chat(username)

        if mode == "group":
            SETTINGS["group_username"] = username
            SETTINGS["group_id"] = chat.id
            await update.message.reply_text(f"✅ گروه ثبت شد\n{username}")

        else:
            SETTINGS["channel_username"] = username
            SETTINGS["channel_id"] = chat.id
            await update.message.reply_text(f"✅ چنل ثبت شد\n{username}")

        context.user_data.clear()
        await update.message.reply_text("🎛 پنل", reply_markup=panel())

    except Exception as e:
        await update.message.reply_text("❌ یوزرنیم پیدا نشد یا ربات دسترسی ندارد")


# ───── فوروارد ─────
async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SETTINGS["forward"]:
        return

    msg = update.message
    if not msg:
        return

    if msg.chat.id != SETTINGS["group_id"]:
        return

    await msg.forward(chat_id=SETTINGS["channel_id"])


# ───── handlers ─────
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(buttons))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username))
tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_all))


# ───── webhook ─────
@app.on_event("startup")
async def startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    await tg_app.start()


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


@app.get("/")
def root():
    return {"status": "running"}

