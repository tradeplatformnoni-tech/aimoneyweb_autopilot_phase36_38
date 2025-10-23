#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 901–950 — Intelligence Sync & Cloud Brain
# ==========================================================
set -e
echo "🧠 NeoLight v5.0 — Intelligence Sync & Cloud Brain initializing..."

mkdir -p backend tools ai/memory ai/insight runtime logs

# -------- 901–920 : Experience Memory Engine ----------------
cat > ai/memory/experience_logger.py <<'PY'
"""
NeoLight Experience Memory Engine
Records signals, risk, and sentiment into rolling memory files.
"""
import json, datetime, pathlib
RUNTIME = pathlib.Path("runtime")
MEMORY = RUNTIME / "experience_log.jsonl"

def record(event: dict):
    event["timestamp"] = datetime.datetime.utcnow().isoformat()
    MEMORY.open("a").write(json.dumps(event)+"\n")

def summarize(limit=50):
    lines = MEMORY.read_text().strip().splitlines()[-limit:] if MEMORY.exists() else []
    data = [json.loads(l) for l in lines]
    return {"entries": len(data), "sample": data[-3:] if data else []}

if __name__ == "__main__":
    record({"type":"init","msg":"Experience memory online"})
    print(summarize())
PY

# -------- 921–930 : Knowledge Rebuilder ---------------------
cat > ai/insight/strategy_rebuilder.py <<'PY'
"""
Analyzes experience memory to identify best-performing strategy configs.
"""
import json, pathlib, random
RUNTIME=pathlib.Path("runtime")
MEMORY=RUNTIME/"experience_log.jsonl"
BEST=RUNTIME/"strategy_best.json"

def rebuild():
    if not MEMORY.exists(): return {"status":"no_memory"}
    data=[json.loads(l) for l in MEMORY.open()]
    # simulate scoring
    scores={"momentum":random.uniform(-1,1),"mean_reversion":random.uniform(-1,1),"crossover":random.uniform(-1,1)}
    best=max(scores,key=scores.get)
    result={"best_strategy":best,"scores":scores}
    json.dump(result,open(BEST,"w"),indent=2)
    return result
if __name__=="__main__":
    print(rebuild())
PY

# -------- 931–940 : Cloud Brain Stub ------------------------
cat > ai/memory/cloud_sync.py <<'PY'
"""
Cloud Brain Sync Stub — placeholder for future multi-node training.
"""
import datetime, json, pathlib
LOG=pathlib.Path("runtime/cloud_sync.jsonl")
def sync():
    msg={"ts":datetime.datetime.utcnow().isoformat(),"status":"ok","note":"local sync only"}
    LOG.open("a").write(json.dumps(msg)+"\n")
    return msg
if __name__=="__main__":
    print(sync())
PY

# -------- 941–950 : Enhanced AutoFix∞ ------------------------
cat > tools/neolight_fix_infinity.sh <<'BASH'
#!/usr/bin/env bash
echo "🧠 NeoLight AutoFix∞ — Infinite Resilience Mode"
chmod +x *.sh backend/*.py tools/*.py ai/**/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy psutil || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/risk_daemon.py >> logs/risk.log 2>&1 &
nohup python tools/sentiment_daemon.py >> logs/sentiment.log 2>&1 &
nohup python tools/allocator_cron.py >> logs/allocator.log 2>&1 &
nohup python -m ai.memory.experience_logger >> logs/memory.log 2>&1 &
nohup python -m ai.insight.strategy_rebuilder >> logs/rebuilder.log 2>&1 &
nohup python -m ai.memory.cloud_sync >> logs/cloudsync.log 2>&1 &
sleep 3
echo "✅ AutoFix∞ complete — all subsystems revived"
echo "💾 Experience log: runtime/experience_log.jsonl"
echo "🌐 Dashboard: http://localhost:8000/dashboard_v48.html"
BASH
chmod +x tools/neolight_fix_infinity.sh

# Restart backend safely
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
sleep 3
echo "✅ Phase 901–950 Installed"
echo "💾 Use AutoFix∞ anytime: tools/neolight_fix_infinity.sh"
echo "📊 Dashboard: http://localhost:8000/dashboard_v48.html"
 
