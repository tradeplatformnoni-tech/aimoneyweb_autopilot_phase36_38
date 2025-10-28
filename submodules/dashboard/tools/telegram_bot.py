import os, asyncio, json
from dotenv import load_dotenv; load_dotenv()
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

BASE = "http://127.0.0.1:8000"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Money Web ready. Commands: /status /positions /mode /sync")

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/api/trading_status",timeout=5).json()
        await update.message.reply_text(f"✅ Eq:{r.get('equity'):.2f} Sig:{r.get('signal'):.3f} DD:{r.get('drawdown'):.2f}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def positions(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/api/positions").json()
        await update.message.reply_text("📦 Positions:\n"+json.dumps(r,indent=2))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        m = " ".join(ctx.args).strip().lower()
        r=requests.post(f"{BASE}/api/mode",json={"mode":m}).json()
        await update.message.reply_text("🔁 "+str(r))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

async def sync(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        r=requests.get(f"{BASE}/sync").json()
        await update.message.reply_text("☁️ "+str(r))
    except Exception as e:
        await update.message.reply_text(f"⚠️ {e}")

def run():
    if not BOT or not CHAT: 
        print("Telegram not configured; set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID"); return
    app=Application.builder().token(BOT).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("mode", mode))
    app.add_handler(CommandHandler("sync", sync))
    app.run_polling()

if __name__=="__main__": run()
