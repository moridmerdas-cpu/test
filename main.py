import os
from fastapi import FastAPI, Request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ───── تنظیمات ─────
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

ADMINS = {123456789, 987654321}  # آیدی عددی ادمین‌ها

SETTINGS = {
    "group": None,     # @groupusername
    "channel": None,   # @channelusername
    "forward": False,
}

app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()


# ───── ابزارها ─────
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن گروه", callback_data="add_group")],
        [InlineKeyboardButton("➕ افزودن چنل", callback_data="add_channel")],
        [
            InlineKeyboardButton("▶️ شروع فوروارد", callback_data="start_forward"),
            InlineKeyboardButton("⏹ توقف فوروارد", callback_data="stop_forward"),
        ],
    ])


# ───── /start ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "🎛 پنل مدیریت",
        reply_markup=panel_keyboard()
    )


# ───── پنل ─────
async def panel_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    data = query.data

    if data == "add_group":
        context.user_data["mode"] = "group"
        await query.message.reply_text("👥 یوزرنیم گروه رو بفرست (مثال: @mygroup)")

    elif data == "add_channel":
        context.user_data["mode"] = "channel"
        await query.message.reply_text("📢 یوزرنیم چنل رو بفرست (مثال: @mychannel)")

    elif data == "start_forward":
        if SETTINGS["group"] and SETTINGS["channel"]:
            SETTINGS["forward"] = True
            await query.message.reply_text("✅ فوروارد شروع شد")
        else:
            await query.message.reply_text("❌ اول گروه و چنل رو تنظیم کن")

    elif data == "stop_forward":
        SETTINGS["forward"] = False
        await query.message.reply_text("⏹ فوروارد متوقف شد")


# ───── دریافت @ ─────
async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    mode = context.user_data.get("mode")
    if not mode:
        return

    text = update.message.text.strip()

    if not text.startswith("@"):
        await update.message.reply_text("❌ باید با @ شروع بشه")
        return

    SETTINGS[mode] = text
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ {mode} تنظیم شد:\n{text}",
        reply_markup=panel_keyboard()
    )


# ───── فوروارد ─────
async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SETTINGS["forward"]:
        return

    message = update.message
    if not message:
        return

    if message.chat.username != SETTINGS["group"].replace("@", ""):
        return

    try:
        await message.forward(chat_id=SETTINGS["channel"])
    except Exception as e:
        print("Forward error:", e)


# ───── هندلرها ─────
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(panel_actions))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username))
tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_all))


# ───── Webhook ─────
@app.on_event("startup")
async def startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    await tg_app.start()
    print("Webhook connected")


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "running"}
