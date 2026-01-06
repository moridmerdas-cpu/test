import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()

LINKS = {
    "group": None,
    "channel": None,
}

# ───────────── /start ─────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="panel")]]
    await update.message.reply_text(
        "سلام 👋\nبه ربات مدیریت خوش اومدی",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ───────────── PANEL ─────────────
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("➕ اتصال گروه", callback_data="set_group")],
        [InlineKeyboardButton("➕ اتصال چنل", callback_data="set_channel")],
    ]

    await query.edit_message_text(
        "انتخاب کن 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ───────────── SET GROUP / CHANNEL ─────────────
async def set_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "set_group":
        context.user_data["mode"] = "group"
        await query.edit_message_text("لینک گروه رو بفرست (مثال: @mygroup)")
    else:
        context.user_data["mode"] = "channel"
        await query.edit_message_text("لینک چنل رو بفرست (مثال: @mychannel)")

# ───────────── RECEIVE LINK ─────────────
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    mode = context.user_data.get("mode")

    if not mode:
        return

    if not text.startswith("@"):
        await update.message.reply_text("❌ لینک باید با @ شروع بشه")
        return

    LINKS[mode] = text
    await update.message.reply_text(f"✅ {mode} وصل شد:\n{text}")
    context.user_data.clear()

# ───────────── FORWARD ALL ─────────────
async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not LINKS["group"] or not LINKS["channel"]:
        return

    try:
        await update.message.forward(chat_id=LINKS["channel"])
    except Exception:
        pass

# ───────────── HANDLERS ─────────────
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CallbackQueryHandler(panel, pattern="panel"))
tg_app.add_handler(CallbackQueryHandler(set_link, pattern="set_"))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link))
tg_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_all))

# ───────────── WEBHOOK ─────────────
@app.on_event("startup")
async def startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    await tg_app.start()
    print("✅ Webhook set")

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "running"}
