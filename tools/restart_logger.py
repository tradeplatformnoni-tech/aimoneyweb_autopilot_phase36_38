import datetime, os, requests

timestamp = datetime.datetime.now().isoformat()
log_line = f"Restarted at {timestamp}\n"
os.makedirs("logs", exist_ok=True)
with open("logs/restart_log.txt", "a") as f:
    f.write(log_line)

print("🧠 Logged restart:", timestamp)

# Optional — Telegram notification if you set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
from dotenv import load_dotenv
load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if token and chat_id:
    msg = f"🚀 AI Money Web restarted successfully at {timestamp}"
    requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={"chat_id": chat_id, "text": msg})

