#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 801–850 — Cloud AI Advisor & Self-Optimization
# - Adds risk & sentiment DAEMONS (fixes missing files)
# - Exposes /api/risk, /api/sentiment/latest, /api/advisor
# - Schedules Goal-Adaptive Allocator
# - AutoFix-aware restarts
# ==========================================================
set -e

echo "🧠 NeoLight :: Phase 801–850 — Cloud AI Advisor & Self-Optimization"

# --- Basics & deps ---
mkdir -p backend tools ai/risk ai/sentiment ai/allocators runtime logs
if [ ! -d ".venv" ] && [ ! -d ".venv" ]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip >/dev/null
pip install --quiet fastapi uvicorn requests pandas numpy psutil python-multipart

echo 'export PYTHONPATH=$(pwd)' > .venv/bin/activate_pathfix
chmod +x .venv/bin/activate_pathfix
source .venv/bin/activate_pathfix

# --- Runtime seeds ---
[ -f runtime/goal_config.json ] || cat > runtime/goal_config.json <<'JSON'
{
  "target_milestones": {
    "2_years": 1000000,
    "5_years": 10000000,
    "10_years": 50000000
  },
  "current_equity": 25000,
  "growth_target": 0.035,
  "risk_tolerance": "medium"
}
JSON
touch runtime/agent_log.jsonl runtime/signals.jsonl

# ==========================================================
# 801–810: Risk Engine (compute metrics on a loop)
# ==========================================================
cat > ai/risk/risk_engine.py <<'PY'
import json, numpy as np, datetime, pathlib, random
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"risk_metrics.json"

def compute_from_equity_series(eq):
    ret = np.diff(eq)/eq[:-1] if len(eq)>1 else np.array([0.0])
    volatility = float(np.std(ret)*np.sqrt(252)) if ret.size>1 else 0.0
    sharpe = float((np.mean(ret)/(np.std(ret)+1e-9))*np.sqrt(252)) if ret.size>2 else 0.0
    var95 = float(np.percentile(ret,5)) if ret.size>1 else 0.0
    drawdown = float(((eq - np.maximum.accumulate(eq))/np.maximum.accumulate(eq)).min()) if len(eq)>0 else 0.0
    return volatility, sharpe, var95, drawdown

def compute():
    # Simulation-safe equity curve (replace with portfolio history later)
    eq = 100000 + np.cumsum(np.random.normal(0, 120, 300))
    vol, sharpe, var95, dd = compute_from_equity_series(eq)
    metrics = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "volatility": vol, "sharpe": sharpe,
        "var_95": var95, "max_drawdown": dd
    }
    json.dump(metrics, open(OUT,"w"), indent=2)
    return metrics
PY

cat > tools/risk_daemon.py <<'PY'
import time, traceback
from ai.risk.risk_engine import compute

if __name__=="__main__":
    print("📊 Risk daemon started (every 120s)")
    while True:
        try:
            compute()
        except Exception:
            traceback.print_exc()
        time.sleep(120)
PY

# ==========================================================
# 811–820: Sentiment Stub (periodic log)
# ==========================================================
cat > ai/sentiment/sentiment_stub.py <<'PY'
import random, datetime, json, pathlib
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"sentiment_log.jsonl"

def analyze(text="market outlook"):
    score = round(random.uniform(-1,1), 2)
    mood = "bullish" if score>0.25 else "bearish" if score<-0.25 else "neutral"
    data = {"timestamp": datetime.datetime.utcnow().isoformat(), "text": text, "score": score, "mood": mood}
    OUT.open("a").write(json.dumps(data)+"\n")
    return data
PY

cat > tools/sentiment_daemon.py <<'PY'
import time, traceback, random
from ai.sentiment.sentiment_stub import analyze

if __name__=="__main__":
    print("📰 Sentiment daemon started (every 90s)")
    samples = [
        "tech earnings beat expectations",
        "inflation concerns rising",
        "ai sector momentum surges",
        "crypto range-bound, volatility compressing"
    ]
    while True:
        try:
            analyze(random.choice(samples))
        except Exception:
            traceback.print_exc()
        time.sleep(90)
PY

# ==========================================================
# 821–830: Advisor Routes (serves risk + last sentiment)
# ==========================================================
cat > backend/advisor_routes.py <<'PY'
from fastapi import APIRouter
import json, pathlib

router = APIRouter()

RISK = pathlib.Path("runtime/risk_metrics.json")
SENT = pathlib.Path("runtime/sentiment_log.jsonl")

@router.get("/api/risk")
def api_risk():
    return json.load(open(RISK)) if RISK.exists() else {}

@router.get("/api/sentiment/latest")
def api_sent_latest():
    if not SENT.exists(): return {}
    lines = SENT.read_text().strip().splitlines()
    return json.loads(lines[-1]) if lines else {}

@router.get("/api/advisor")
def api_advisor():
    risk = json.load(open(RISK)) if RISK.exists() else {}
    sent = {}
    if SENT.exists():
        lines = SENT.read_text().strip().splitlines()
        if lines: sent = json.loads(lines[-1])
    return {"risk": risk, "last_sentiment": sent}
PY

# Inject advisor routes into backend/main.py if not present
if ! grep -q "advisor_routes" backend/main.py; then
  # add import
  sed -i.bak '1s|^|from backend.advisor_routes import router as advisor_router\n|' backend/main.py
  # include router after app = FastAPI(...)
  sed -i '' 's|app = FastAPI.*|&\napp.include_router(advisor_router)|' backend/main.py
fi

# ==========================================================
# 831–850: Self-Optimization — Goal-Adaptive Allocator cron
# ==========================================================
cat > tools/allocator_cron.py <<'PY'
import time, traceback
from ai.allocators.goal_allocator import adapt

if __name__=="__main__":
    print("⚖️ Goal-allocator cron started (every 10 minutes)")
    while True:
        try:
            adapt()
        except Exception:
            traceback.print_exc()
        time.sleep(600)
PY

# (Ensure allocator exists — from earlier phase. If not, create minimal.)
if [ ! -f ai/allocators/goal_allocator.py ]; then
cat > ai/allocators/goal_allocator.py <<'PY'
import json, pathlib
CFG=pathlib.Path("runtime/goal_config.json")
WFILE=pathlib.Path("runtime/portfolio_weights.json")
def adapt():
    if not CFG.exists(): return
    if not WFILE.exists():
        json.dump({"momentum":0.34,"crossover":0.33,"mean_reversion":0.33}, open(WFILE,"w"), indent=2)
    cfg=json.load(open(CFG)); w=json.load(open(WFILE))
    cur=cfg.get("current_equity",100000); tgt=cfg.get("target_milestones",{}).get("2_years",1000000)
    ratio=min(max(cur/float(tgt),0.0),1.0) if tgt else 0.0
    w["momentum"]=round(0.3+0.2*ratio,2)
    w["mean_reversion"]=round(0.4-0.2*ratio,2)
    w["crossover"]=round(max(0.0,1 - w["momentum"] - w["mean_reversion"]),2)
    json.dump(w, open(WFILE,"w"), indent=2)
    return w
PY
fi

# ==========================================================
# AutoFix upgrade helper (optional callable)
# ==========================================================
cat > tools/neolight_fix_upgrade.sh <<'BASH'
#!/usr/bin/env bash
echo "🧠 NeoLight Enhanced AutoFix…"
chmod +x *.sh backend/*.py tools/*.py ai/**/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy psutil || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
sleep 2
echo "✅ AutoFix OK — Visit http://localhost:8000/dashboard"
BASH
chmod +x tools/neolight_fix_upgrade.sh

# ==========================================================
# Restart services (backend + new daemons)
# ==========================================================
echo "♻️ Restarting backend + daemons"
pkill -f "tools/risk_daemon.py" || true
pkill -f "tools/sentiment_daemon.py" || true
pkill -f "tools/allocator_cron.py" || true
pkill -f "uvicorn backend.main:app" || true

nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/risk_daemon.py       >> logs/risk.log      2>&1 &
nohup python tools/sentiment_daemon.py  >> logs/sentiment.log 2>&1 &
nohup python tools/allocator_cron.py    >> logs/allocator.log 2>&1 &

sleep 2
echo "✅ Phase 801–850 installed."
echo "👉 Health:     curl http://127.0.0.1:8000/api/health"
echo "👉 Risk:       curl http://127.0.0.1:8000/api/risk"
echo "👉 Sentiment:  curl http://127.0.0.1:8000/api/sentiment/latest"
echo "👉 Advisor:    curl http://127.0.0.1:8000/api/advisor"
echo "👉 Dashboard:  http://localhost:8000/dashboard"
echo "👉 AutoFix:    neolight-fix   OR   tools/neolight_fix_upgrade.sh"

