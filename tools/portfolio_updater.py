import os, json, datetime, requests
from dotenv import load_dotenv
load_dotenv()

ALPACA_KEY = os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY","")
PAPER_BASE = os.getenv("ALPACA_PAPER_BASE","https://paper-api.alpaca.markets/v2")

HEADERS = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET}

def fetch_positions():
    r = requests.get(f"{PAPER_BASE}/positions", headers=HEADERS, timeout=20)
    return r.json() if r.status_code == 200 else []

def fetch_account():
    r = requests.get(f"{PAPER_BASE}/account", headers=HEADERS, timeout=20)
    return r.json() if r.status_code == 200 else {}

if __name__ == "__main__":
    snap = {
        "timestamp": datetime.datetime.now().isoformat(),
        "account": fetch_account(),
        "positions": fetch_positions()
    }
    os.makedirs("logs", exist_ok=True)
    json.dump(snap, open("logs/dashboard_portfolio.json","w"), indent=2)
    print("✅ Portfolio snapshot updated.")
