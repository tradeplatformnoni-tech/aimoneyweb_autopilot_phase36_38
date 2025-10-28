#!/bin/bash
echo "🚀 Phase 3401–3450: Dependencies + Env + Portfolio Sync"
echo "-------------------------------------------------------"

# 0) Locate venv python/pip reliably
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python3" ]; then
  PY="$VIRTUAL_ENV/bin/python3"
  PIP="$VIRTUAL_ENV/bin/pip"
elif [ -x "./venv/bin/python3" ]; then
  PY="./venv/bin/python3"
  PIP="./venv/bin/pip"
else
  echo "❗ Could not find venv. Create one: python3 -m venv venv && source venv/bin/activate"
  exit 1
fi
echo "🧠 Using Python: $($PY -c 'import sys; print(sys.executable)')"

# 1) Install required packages into the venv
echo "📦 Installing deps into venv..."
$PIP install -q requests python-dotenv psutil fastapi uvicorn || {
  echo "❗ pip install failed"; exit 1; }

# 2) Ensure .env (Alpaca) exists (create sample if missing)
if [ ! -f .env ]; then
  cat > .env <<'EOF'
# Fill these with your real paper/live keys, then restart.
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
# Optional: override Alpaca base URLs if needed
# ALPACA_PAPER_BASE=https://paper-api.alpaca.markets/v2
# ALPACA_DATA_BASE=https://data.alpaca.markets/v2
EOF
  echo "🗝️ Created .env (empty). Edit it to add ALPACA_API_KEY and ALPACA_SECRET_KEY."
fi

# 3) Patch providers/updater to load dotenv (idempotent)
mkdir -p ai/providers tools api/core config logs

# alpaca_provider.py (loads OHLC; supports data base override)
cat > ai/providers/alpaca_provider.py <<'EOF'
import os, json, requests
from dotenv import load_dotenv
load_dotenv()

ALPACA_KEY = os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY","")

DATA_BASE = os.getenv("ALPACA_DATA_BASE","https://data.alpaca.markets/v2")

def get_ohlc(symbol, timeframe="1Day", limit=60):
    # For crypto symbols like BTC/USD, Alpaca uses "BTCUSD"
    alpaca_symbol = symbol.replace("/","")
    # Stocks use /stocks/, crypto uses /crypto/
    is_crypto = "/" in symbol or any(x in symbol for x in ["BTC","ETH","SOL","XRP","BNB","USDT"])
    path = f"/crypto/{alpaca_symbol}/bars" if is_crypto else f"/stocks/{alpaca_symbol}/bars"
    url = f"{DATA_BASE}{path}?timeframe={timeframe}&limit={limit}"
    headers = {
      "APCA-API-KEY-ID": ALPACA_KEY,
      "APCA-API-SECRET-KEY": ALPACA_SECRET
    }
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
      return []
    data = r.json()
    return data.get("bars", [])
EOF

# portfolio_updater.py (loads dotenv; supports paper base override)
cat > tools/portfolio_updater.py <<'EOF'
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
EOF

# 4) Portfolio API route (returns dashboard_portfolio.json)
cat > api/core/portfolio_routes.py <<'EOF'
from fastapi import APIRouter
import json, os
router = APIRouter()

@router.get("/api/portfolio/data")
def portfolio_data():
    f = "logs/dashboard_portfolio.json"
    if not os.path.exists(f):
        return {"positions": [], "account": {}}
    try:
        return json.load(open(f))
    except Exception as e:
        return {"error": str(e), "positions": [], "account": {}}
EOF

# 5) Wire portfolio route into backend/main.py (idempotent)
MAIN="backend/main.py"
if ! grep -q "portfolio_routes" "$MAIN"; then
  echo "🔗 Injecting portfolio route into backend..."
  # Import line
  sed -i '' '/from fastapi import FastAPI/a\
from api.core import portfolio_routes' "$MAIN"
  # Include line (after app = FastAPI())
  sed -i '' '/app = FastAPI()/a\
app.include_router(portfolio_routes.router)' "$MAIN"
fi

# 6) Create minimal symbols.json if missing
if [ ! -f config/symbols.json ]; then
  cat > config/symbols.json <<'EOF'
[
  "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
  "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "BNB/USD",
  "GOLD", "SILVER"
]
EOF
  echo "💹 Created default config/symbols.json"
fi

# 7) Quick signal generator sanity check (optional; uses provider)
cat > ai/signal_engine.py <<'EOF'
import json, datetime, random
from ai.providers import alpaca_provider

symbols = json.load(open("config/symbols.json"))
def generate_signals():
    out = []
    for sym in symbols:
        bars = alpaca_provider.get_ohlc(sym, limit=3)
        if not bars: 
            continue
        price = float(bars[-1].get("c", 0))
        out.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "strategy": random.choice(["momentum","crossover","mean_reversion"]),
            "symbol": sym,
            "signal": random.choice(["BUY","SELL","HOLD"]),
            "confidence": round(random.uniform(0.5,0.99),2),
            "price": price
        })
    if out:
        open("logs/signals.jsonl","a").write("\n".join([json.dumps(x) for x in out])+"\n")
        print(f"✅ Wrote {len(out)} signals.")
    else:
        print("ℹ️ No bars returned (check API keys or symbols).")

if __name__ == "__main__":
    generate_signals()
EOF

# 8) Restart backend (use venv python/uvicorn)
echo "🔁 Restarting FastAPI..."
pkill -f uvicorn 2>/dev/null
nohup $PY -m uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
sleep 2

# 9) First portfolio snapshot (will be empty if .env keys not set)
echo "📈 Updating portfolio snapshot..."
$PY tools/portfolio_updater.py || echo "ℹ️ Skipped updater (check .env keys)."

echo "✅ Phase 3401–3450 completed."
echo "👉 Next: edit .env and rerun 'python3 tools/portfolio_updater.py' when keys are set."

