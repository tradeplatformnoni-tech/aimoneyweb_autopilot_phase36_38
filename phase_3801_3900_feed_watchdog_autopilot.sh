#!/bin/bash
echo "🚀 Phase 3801–3900: Feed Watchdog + Auto-Alert + Commodity Fallback Autopilot"
echo "------------------------------------------------------------"

mkdir -p ai/watchdog logs config tools ai/providers

# === 1️⃣  Commodity & Crypto Fallback Provider ===
cat > ai/providers/fallback_provider.py <<'EOF'
import requests, datetime, time, random

# --- Yahoo Finance for Commodities ---
def get_commodity_price(symbol):
    yahoo_map = {
        "GOLD": "GC=F",
        "SILVER": "SI=F"
    }
    if symbol not in yahoo_map:
        return None
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_map[symbol]}?interval=1h&range=1d"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()["chart"]["result"][0]
        close_prices = data["indicators"]["quote"][0]["close"]
        timestamps = data["timestamp"]
        bars = []
        for t, c in zip(timestamps, close_prices):
            if c is not None:
                bars.append({
                    "t": datetime.datetime.fromtimestamp(t).isoformat(),
                    "o": c, "h": c, "l": c, "c": c
                })
        print(f"🪙 Fetched {len(bars)} bars for {symbol} from Yahoo Finance")
        return bars
    except Exception as e:
        print(f"⚠️ Yahoo fallback failed for {symbol}: {e}")
        return []

# --- CoinGecko for Crypto Fallback ---
def get_crypto_price(symbol):
    cg_map = {
        "BTC/USD": "bitcoin",
        "ETH/USD": "ethereum",
        "SOL/USD": "solana"
    }
    if symbol not in cg_map:
        return None
    coin = cg_map[symbol]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()["prices"]
        bars = []
        for t, c in data[-60:]:
            bars.append({
                "t": datetime.datetime.fromtimestamp(t/1000).isoformat(),
                "o": c, "h": c, "l": c, "c": c
            })
        print(f"💰 Fetched {len(bars)} bars for {symbol} from CoinGecko")
        return bars
    except Exception as e:
        print(f"⚠️ CoinGecko fallback failed for {symbol}: {e}")
        return []
EOF

# === 2️⃣  Feed Watchdog Daemon ===
cat > ai/watchdog/feed_watchdog.py <<'EOF'
import os, time, json
from ai.providers.data_feed import get_bars_for_symbol
from ai.providers.fallback_provider import get_commodity_price, get_crypto_price
from tools.alert_notify import send_alert

LOG_PATH = "logs/watchdog.log"

def watchdog_loop():
    with open("config/symbols.json") as f:
        symbols = json.load(f)
    while True:
        for sym in symbols:
            bars = get_bars_for_symbol(sym, limit=5)
            if not bars:
                print(f"⚠️ Feed failure for {sym} — attempting fallback ...")
                if "/" in sym:
                    fb = get_crypto_price(sym)
                else:
                    fb = get_commodity_price(sym)
                if fb:
                    print(f"✅ Fallback success for {sym}")
                else:
                    msg = f"🚨 Feed still down for {sym} after fallback attempt"
                    print(msg)
                    send_alert(msg)
                with open(LOG_PATH, "a") as log:
                    log.write(f"{time.asctime()} — {sym} fallback attempted\n")
            else:
                print(f"✅ Feed OK for {sym}")
            time.sleep(5)
        print("🔁 Next Watchdog cycle ...")
        time.sleep(60)

if __name__ == "__main__":
    print("🧠 Starting Feed Watchdog ...")
    watchdog_loop()
EOF

# === 3️⃣  Update neolight-fix with New Diagnostics ===
if ! grep -q "watchdog.log" neolight-fix 2>/dev/null; then
cat >> neolight-fix <<'EOF'

echo "🩺 Checking Feed Watchdog Logs..."
tail -n 10 logs/watchdog.log || echo "❗ No watchdog logs found"

echo "📊 Running Feed Self-Test..."
python3 ai/watchdog/feed_watchdog.py & sleep 3 && pkill -f feed_watchdog.py
EOF
fi

echo "✅ Phase 3801–3900 Autopilot Complete — Feed Watchdog Active !"
echo "------------------------------------------------------------"

