#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 711–760  —  Intelligence & Resilience Layer
# ==========================================================
set -e

echo "🧠 NeoLight :: Phase 711–760  (Signal + Alerts + Snapshots + Alloc + AutoFix)"

mkdir -p backend tools ai/enrichment ai/allocators runtime logs

# ------------- 711–720 : Signal Enrichment -----------------
cat > ai/enrichment/enrich_signals.py <<'PY'
"""
Adds confidence/volatility metrics to signals before logging.
Simulation-safe; no external data pulled.
"""
import json, math, random, datetime, pathlib
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"signals_enriched.jsonl"

def enrich(signal: dict):
    base = signal.copy()
    closes = [random.uniform(90,110) for _ in range(20)]
    volatility = round(float(max(closes)-min(closes))/sum(closes)*len(closes)*100,2)
    confidence = round(100 - volatility + random.uniform(-5,5),2)
    base.update({
        "volatility": volatility,
        "confidence": confidence,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    OUT.open("a").write(json.dumps(base)+"\n")
    return base

if __name__ == "__main__":
    s = {"strategy":"demo","symbol":"AAPL","signal":"BUY"}
    print(enrich(s))
PY

# ------------- 721–730 : Trade Alert Formatter -------------
cat > backend/alert_formatter.py <<'PY'
"""
Formats enriched signals into pretty Discord/Telegram messages.
"""
def format_alert(sig):
    s = sig.get("signal","HOLD")
    emo = "📈" if s=="BUY" else "📉" if s=="SELL" else "🤖"
    msg = f"{emo}  {sig.get('strategy','?')} suggests **{s}** {sig.get('symbol','')} @ conf. {sig.get('confidence',0)}%"
    return msg
PY

# ------------- 731–740 : Portfolio Snapshot ----------------
cat > tools/snapshot_daemon.py <<'PY'
"""
Simulated snapshot writer.  Appends equity history to runtime/snapshots.jsonl.
"""
import time, json, datetime, random, pathlib
RUNTIME=pathlib.Path("runtime"); FILE=RUNTIME/"snapshots.jsonl"
def loop():
    while True:
        eq=100000+random.uniform(-500,500)
        snap={"ts":datetime.datetime.utcnow().isoformat(),"equity":eq}
        FILE.open("a").write(json.dumps(snap)+"\n")
        time.sleep(300)
if __name__=="__main__": loop()
PY

# ------------- 741–750 : Live Execution Bridge (placeholder) -------------
cat > ai/providers/live_bridge.py <<'PY'
"""
Disabled-by-default execution bridge.
Enable later by adding API keys and uncommenting trade() logic.
"""
import os, json
def trade(order):
    # --- PLACEHOLDER ---
    # Example structure only:
    # if os.getenv("ALPACA_API_KEY"):
    #     # send live order to Alpaca / Binance
    #     pass
    return {"status":"disabled","order":order}
PY

# ------------- 751–760 : Goal-Adaptive Allocator -------------
cat > ai/allocators/goal_allocator.py <<'PY'
"""
Adjusts strategy weights based on progress toward wealth goals.
"""
import json, pathlib
CFG=pathlib.Path("runtime/goal_config.json")
WFILE=pathlib.Path("runtime/portfolio_weights.json")

def adapt():
    if not CFG.exists() or not WFILE.exists(): return
    cfg=json.load(open(CFG)); w=json.load(open(WFILE))
    cur=cfg.get("current_equity",100000); tgt=cfg.get("target_milestones",{}).get("2_years",1000000)
    ratio=min(cur/tgt,1.0)
    w["momentum"]=round(0.3+0.2*ratio,2)
    w["mean_reversion"]=round(0.4-0.2*ratio,2)
    w["crossover"]=round(1-w["momentum"]-w["mean_reversion"],2)
    json.dump(w,open(WFILE,"w"),indent=2)
    return w

if __name__=="__main__":
    print(adapt())
PY

# ------------- Restart & AutoFix Pilot Hook -----------------
echo "♻️  Restarting backend + daemons"
pkill -f "tools/snapshot_daemon.py" || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/snapshot_daemon.py >> logs/snapshot.log 2>&1 &

echo "✅  Phase 711–760 modules installed."
echo "👉  Heal anytime with:  neolight-fix"
echo "👉  Check health:       curl http://127.0.0.1:8000/api/health"
echo "👉  Dashboard:          http://localhost:8000/dashboard"

