import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات وصل شد")

tg_app.add_handler(CommandHandler("start", start))


@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(WEBHOOK_URL)
    await tg_app.start()
    print("Webhook set")


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


@app.get("/")
def home():
    return {"status": "running"}
