#!/bin/bash
echo "🚀 Phase 3001–3200: Multi-Asset Portfolio Expansion + Dashboard Sync"
echo "--------------------------------------------------------------------"

# 1️⃣ Ensure config folder exists
mkdir -p config logs ai tools

# 2️⃣ Expand symbol universe
cat > config/symbols.json <<'EOF'
[
  "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
  "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "BNB/USD",
  "GOLD", "SILVER"
]
EOF
echo "💹 Multi-asset symbols.json created."

# 3️⃣ Portfolio updater (pulls Alpaca data for all assets)
cat > tools/portfolio_updater.py <<'EOF'
"""
tools/portfolio_updater.py
Fetches positions and account stats from Alpaca and writes them to logs/dashboard_portfolio.json.
"""
import json, os, datetime, requests

ALPACA_KEY=os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET=os.getenv("ALPACA_SECRET_KEY","")
BASE="https://paper-api.alpaca.markets/v2"

headers={"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}

def fetch_positions():
    r=requests.get(f"{BASE}/positions",headers=headers)
    if r.status_code!=200: return []
    return r.json()

def fetch_account():
    r=requests.get(f"{BASE}/account",headers=headers)
    if r.status_code!=200: return {}
    return r.json()

if __name__=="__main__":
    data={
        "timestamp":datetime.datetime.now().isoformat(),
        "account":fetch_account(),
        "positions":fetch_positions()
    }
    os.makedirs("logs",exist_ok=True)
    json.dump(data,open("logs/dashboard_portfolio.json","w"),indent=2)
    print("✅ Portfolio snapshot updated.")
EOF
echo "📈 Portfolio updater added."

# 4️⃣ Dashboard data endpoint
cat > api/core/portfolio_routes.py <<'EOF'
from fastapi import APIRouter
import json, os

router=APIRouter()

@router.get("/api/portfolio/data")
def portfolio_data():
    f="logs/dashboard_portfolio.json"
    if not os.path.exists(f): return {"positions":[],"account":{}}
    return json.load(open(f))
EOF

# 5️⃣ Hook portfolio route into backend
MAIN="backend/main.py"
if ! grep -q "portfolio_routes" "$MAIN"; then
  sed -i '' '/from api.core import routes/a\
from api.core import portfolio_routes' "$MAIN"
  sed -i '' '/app.include_router(core_routes.router)/a\
app.include_router(portfolio_routes.router)' "$MAIN"
  echo "🔗 Portfolio route linked into backend."
fi

# 6️⃣ Update frontend JS (adds positions + metrics rendering)
cat > ui/static/dashboard.js <<'EOF'
// dashboard.js - renders live positions & metrics
async function loadPortfolio() {
  const res = await fetch('/api/portfolio/data');
  const data = await res.json();
  const posDiv = document.getElementById('positions');
  posDiv.innerHTML = '<h4>Positions</h4>' + data.positions.map(
    p => `<div>${p.symbol}: ${parseFloat(p.market_value).toFixed(2)} (${p.qty})</div>`
  ).join('');
}
setInterval(loadPortfolio, 10000);
EOF
echo "🧠 Dashboard auto-refresh for positions added."

# 7️⃣ Schedule portfolio updates every 5 min
cat > tools/portfolio_daemon.sh <<'EOF'
#!/bin/bash
while true
do
  echo "🧠 Updating portfolio snapshot..."
  python3 tools/portfolio_updater.py
  sleep 300
done
EOF
chmod +x tools/portfolio_daemon.sh
nohup ./tools/portfolio_daemon.sh > logs/portfolio_daemon.log 2>&1 &
echo "📊 Portfolio daemon running."

# 8️⃣ Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted with new data sources."

# 9️⃣ Optional mobile alert
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "📈 Phase 3001–3200 Active | Multi-Asset + Live Dashboard Connected"

echo "✅ Autopilot complete for Phase 3001–3200."

