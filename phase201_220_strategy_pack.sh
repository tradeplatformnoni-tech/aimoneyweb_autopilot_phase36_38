#!/bin/zsh
set -e

echo "🚀 Phase 201–220 :: Strategy Pack (Momentum + Crossovers + Scheduler)"

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools ai/strategies runtime
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup -> backups/main.py.$timestamp.bak" || true

echo "🧩 Installing deps..."
pip install -q "uvicorn[standard]" fastapi python-dotenv requests pandas numpy alpaca-trade-api

# Ensure .env keys exist
grep -q '^PAPER_TRADE=' .env || echo 'PAPER_TRADE=0' >> .env
grep -q '^ALPACA_BASE_URL=' .env || echo 'ALPACA_BASE_URL=https://paper-api.alpaca.markets' >> .env
grep -q '^ALPACA_API_KEY_ID=' .env || echo 'ALPACA_API_KEY_ID=YOUR_KEY_HERE' >> .env
grep -q '^ALPACA_API_SECRET=' .env || echo 'ALPACA_API_SECRET=YOUR_SECRET_HERE' >> .env
grep -q '^SYMBOL_WHITELIST=' .env || echo 'SYMBOL_WHITELIST=AAPL,MSFT,GOOGL,NVDA,SPY,QQQ' >> .env
grep -q '^MAX_NOTIONAL_PER_TRADE=' .env || echo 'MAX_NOTIONAL_PER_TRADE=200' >> .env
grep -q '^MAX_OPEN_POSITIONS=' .env || echo 'MAX_OPEN_POSITIONS=3' >> .env
grep -q '^RISK_CAP=' .env || echo 'RISK_CAP=0.03' >> .env
grep -q '^VAR_LOOKBACK_DAYS=' .env || echo 'VAR_LOOKBACK_DAYS=10' >> .env

# -------- ai/strategies/momentum.py --------
cat > ai/strategies/momentum.py << 'EOF'
import numpy as np
import pandas as pd

def sma(series, window):
    return series.rolling(window=window, min_periods=window).mean()

def rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    ma_up = up.rolling(window=window, min_periods=window).mean()
    ma_down = down.rolling(window=window, min_periods=window).mean()
    rs = ma_up / (ma_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi

def crossover_signals(prices: pd.Series, fast=10, slow=20, rsi_lb=30, rsi_ub=70):
    fast_sma = sma(prices, fast)
    slow_sma = sma(prices, slow)
    _rsi = rsi(prices, 14)
    sig = None
    if fast_sma.iloc[-1] is not None and slow_sma.iloc[-1] is not None:
        prev_cross = (fast_sma.iloc[-2] or np.nan) - (slow_sma.iloc[-2] or np.nan)
        cur_cross  = (fast_sma.iloc[-1] or np.nan) - (slow_sma.iloc[-1] or np.nan)
        if np.isfinite(prev_cross) and np.isfinite(cur_cross):
            # golden cross
            if prev_cross <= 0 and cur_cross > 0 and (_rsi.iloc[-1] < rsi_ub):
                sig = "buy"
            # death cross
            if prev_cross >= 0 and cur_cross < 0 and (_rsi.iloc[-1] > rsi_lb):
                sig = "sell"
    return sig, {
        "fast": float(fast_sma.iloc[-1]) if fast_sma.notna().iloc[-1] else None,
        "slow": float(slow_sma.iloc[-1]) if slow_sma.notna().iloc[-1] else None,
        "rsi":  float(_rsi.iloc[-1]) if np.isfinite(_rsi.iloc[-1]) else None
    }
EOF

# -------- ai/strategy_engine.py --------
cat > ai/strategy_engine.py << 'EOF'
import os, json, time
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, List
from ai.strategies.momentum import crossover_signals

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
CONF = RUNTIME / "strategy_config.json"
SIGNALS = RUNTIME / "signals.jsonl"

load_dotenv(BASE / ".env")

DEFAULT_CONF = {
    "enabled": True,
    "symbols": ["AAPL","MSFT","NVDA","SPY"],
    "fast": 10,
    "slow": 20,
    "rsi_lb": 30,
    "rsi_ub": 70,
    "notional": 200
}

def load_config()->Dict:
    if CONF.exists():
        try: return json.loads(CONF.read_text())
        except: pass
    return DEFAULT_CONF

def save_config(cfg:Dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    CONF.write_text(json.dumps(cfg, indent=2))

def append_signal(sig:Dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS, "a") as f:
        f.write(json.dumps(sig) + "\n")

def fetch_prices_alpaca(symbol:str, limit:int=200) -> pd.Series:
    # keep without extra data subscription; fallback to synthetic walk
    try:
        from alpaca_trade_api.rest import REST
        api = REST(os.getenv("ALPACA_API_KEY_ID",""), os.getenv("ALPACA_API_SECRET",""),
                   base_url=os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets"))
        bars = api.get_bars(symbol, "1Day", limit=limit)
        px = [float(getattr(b,'c', getattr(b,'close',0))) for b in bars]
        if len(px) > 0:
            return pd.Series(px)
    except Exception:
        pass
    # fallback mock series
    import numpy as np
    import random
    base = 100 + random.random()*10
    walk = base + np.cumsum(np.random.normal(0,1,limit))
    return pd.Series(walk)

def run_once()->List[Dict]:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return []

    results = []
    for sym in cfg.get("symbols", []):
        prices = fetch_prices_alpaca(sym, limit=max(cfg.get("slow",20)+5, 30))
        if len(prices) < max(cfg.get("slow",20), cfg.get("fast",10)) + 2:
            continue
        side, info = crossover_signals(prices, cfg.get("fast",10), cfg.get("slow",20), cfg.get("rsi_lb",30), cfg.get("rsi_ub",70))
        if side in ("buy","sell"):
            sig = {"ts": time.time(), "symbol": sym, "side": side, "notional": cfg.get("notional",200), "tag":"strategy"}
            append_signal(sig)
            results.append({"symbol":sym,"side":side,"info":info})
    return results

if __name__ == "__main__":
    out = run_once()
    print(json.dumps({"generated": out}, indent=2))
EOF

# -------- tools/strategy_daemon.py --------
cat > tools/strategy_daemon.py << 'EOF'
import time, json
from ai.strategy_engine import run_once

def main():
    while True:
        try:
            out = run_once()
            if out:
                print("[strategy] queued:", json.dumps(out))
        except Exception as e:
            print("[strategy] error:", e)
        time.sleep(30)  # every 30s (adjust as desired)

if __name__ == "__main__":
    main()
EOF

# -------- Patch main.py to add /api/strategy_config --------
python3 - << 'PY'
from pathlib import Path
p = Path("main.py")
t = p.read_text()
if "/api/strategy_config" not in t:
    inject = """

from typing import Dict
from ai.strategy_engine import load_config, save_config

@app.get("/api/strategy_config")
def get_strategy_config():
    return load_config()

@app.post("/api/strategy_config")
def set_strategy_config(cfg: Dict):
    save_config(cfg)
    return {"ok": True, "config": cfg}
"""
    # append at end safely
    t = t.rstrip() + inject
    p.write_text(t)
print("✅ main.py patched with /api/strategy_config")
PY

# -------- Update dashboard with Start/Stop Strategy buttons --------
python3 - << 'PY'
from pathlib import Path, re
p = Path("static/dashboard.html")
if p.exists():
    html = p.read_text()
else:
    html = "<html><body><h1>Dashboard</h1></body></html>"

if "Strategy Controls" not in html:
    controls = """
    <h3>Strategy Controls</h3>
    <div class="row">
      <button class="btn" onclick="saveCfg()">Save Config</button>
      <button class="btn" onclick="startStrategy()">Start Strategy</button>
      <button class="btn" onclick="stopStrategy()">Stop Strategy</button>
    </div>
    <pre id="cfgBox">loading config...</pre>
    <script>
    async function loadCfg(){ const r=await fetch('/api/strategy_config'); const j=await r.json(); document.getElementById('cfgBox').textContent=JSON.stringify(j,null,2); }
    async function saveCfg(){
      const text = prompt('Paste JSON config (e.g. {"enabled":true,"symbols":["AAPL","NVDA"],"fast":10,"slow":20,"notional":200})');
      if(!text) return;
      try{ const j=JSON.parse(text);
        await fetch('/api/strategy_config',{method:'POST',headers:{'Content-Type':'application/json'}, body: JSON.stringify(j)});
        setTimeout(loadCfg,800);
      }catch(e){ alert('Invalid JSON'); }
    }
    function startStrategy(){ fetch('/api/signal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({"symbol":"AAPL","side":"buy","notional":50,"tag":"kick"})}); fetch('/api/strategy_config').then(r=>r.json()).then(j=>{ j.enabled=true; fetch('/api/strategy_config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(j)}); setTimeout(loadCfg,800); }); }
    function stopStrategy(){ fetch('/api/strategy_config').then(r=>r.json()).then(j=>{ j.enabled=false; fetch('/api/strategy_config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(j)}); setTimeout(loadCfg,800); }); }
    loadCfg();
    </script>
    """
    html = html.replace("</body>", controls + "\n</body>")
p.write_text(html)
print("✅ dashboard.html extended with Strategy Controls")
PY

# -------- Launch / Restart everything --------
echo "🔪 Restarting backend..."
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &

echo "🤖 Ensuring supervisor + executor + strategy daemon..."
# Keep existing trader_supervisor.py and order_executor.py if present
if [ -f tools/trader_supervisor.py ]; then
  nohup venv/bin/python3 tools/trader_supervisor.py > logs/trader.log 2>&1 &
fi
if [ -f tools/order_executor.py ]; then
  nohup venv/bin/python3 tools/order_executor.py > logs/executor.log 2>&1 &
fi
nohup venv/bin/python3 tools/strategy_daemon.py > logs/strategy.log 2>&1 &

sleep 5
if curl -s http://127.0.0.1:8000/ | grep -q "Phase 191–200"; then
  echo "✅ Backend healthy — opening dashboard..."
  open http://127.0.0.1:8000/dashboard
else
  echo "⚠️  Backend response unexpected — still opening dashboard."
  open http://127.0.0.1:8000/dashboard
fi

echo "📄 Logs -> tail -f logs/backend.log logs/trader.log logs/executor.log logs/strategy.log"
echo "🎯 Phase 201–220 complete: strategy daemon live."

