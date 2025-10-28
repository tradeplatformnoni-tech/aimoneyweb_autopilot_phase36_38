#!/usr/bin/env bash
# ==============================================================
# NeoLight :: Phase 761 – 800 — Risk & Sentiment Layer + AutoFix Upgrade
# ==============================================================

set -e
echo "🧠 NeoLight :: Phase 761–800 Starting…"

mkdir -p backend tools ai/risk ai/sentiment runtime logs

# ---------------- 761–770 : Risk Analytics -------------------
cat > ai/risk/risk_engine.py <<'PY'
"""
Computes daily risk metrics: volatility, Sharpe, VaR, drawdown (simulation only).
"""
import json, numpy as np, datetime, pathlib, random
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"risk_metrics.json"
def compute():
    eq = 100000 + np.cumsum(np.random.normal(0,100,100))
    ret = np.diff(eq)/eq[:-1]
    vol = float(np.std(ret)*np.sqrt(252))
    sharpe = float((np.mean(ret)/(np.std(ret)+1e-9))*np.sqrt(252))
    var95 = float(np.percentile(ret,5))
    dd = float(((eq - np.maximum.accumulate(eq))/np.maximum.accumulate(eq)).min())
    metrics = {"timestamp": datetime.datetime.utcnow().isoformat(),
               "volatility": vol, "sharpe": sharpe,
               "var_95": var95, "max_drawdown": dd}
    json.dump(metrics, open(OUT,"w"), indent=2)
    return metrics
if __name__ == "__main__": print(compute())
PY

# ---------------- 771–780 : Sentiment Feed --------------------
cat > ai/sentiment/sentiment_stub.py <<'PY'
"""
Simulated sentiment model. Returns a score -1..1 and mood text.
"""
import random, datetime, json, pathlib
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"sentiment_log.jsonl"
def analyze(text="market outlook positive"):
    score = round(random.uniform(-1,1),2)
    mood = "bullish" if score>0.25 else "bearish" if score<-0.25 else "neutral"
    data = {"timestamp": datetime.datetime.utcnow().isoformat(),
            "text": text, "score": score, "mood": mood}
    OUT.open("a").write(json.dumps(data)+"\n")
    return data
if __name__=="__main__": print(analyze())
PY

# ---------------- 781–790 : Advisor Stub ----------------------
cat > backend/advisor_stub.py <<'PY'
"""
Stub for future AI Advisor. Returns last risk + sentiment summary.
"""
import json, pathlib
RISK=pathlib.Path("runtime/risk_metrics.json")
SENT=pathlib.Path("runtime/sentiment_log.jsonl")
def summarize():
    r=json.load(open(RISK)) if RISK.exists() else {}
    s=[json.loads(l) for l in SENT.open()] if SENT.exists() else []
    last=s[-1] if s else {}
    return {"risk":r,"last_sentiment":last}
PY

# ---------------- 791–800 : AutoFix Upgrade -------------------
cat > tools/neolight_fix_upgrade.sh <<'BASH'
#!/usr/bin/env bash
echo "🧠 Running NeoLight Enhanced AutoFix…"
chmod +x *.sh backend/*.py tools/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
echo "✅ AutoFix Complete — Dashboard at http://localhost:8000/dashboard"
BASH
chmod +x tools/neolight_fix_upgrade.sh

# ---------------- Restart Services ----------------------------
pkill -f "tools/snapshot_daemon.py" || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/snapshot_daemon.py >> logs/snapshot.log 2>&1 &

echo "✅ Phase 761–800 Installed."
echo "👉 Heal anytime with : tools/neolight_fix_upgrade.sh"
echo "👉 Health check      : curl http://127.0.0.1:8000/api/health"

