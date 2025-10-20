#!/bin/zsh
set -e
echo "🌍 Phase 83–90 :: Federated Swarm + Genetic Trainer + Voice Cmd + Global Dashboard …"

mkdir -p backups logs models ai/federation ai/genetic tools static
ts=$(date +"%Y%m%d_%H%M%S")
[ -f main.py ] && cp main.py backups/main.py.$ts.bak && echo "✅ Backup → backups/main.py.$ts.bak"

# Deps (only light libs; speech is file-driven to avoid mic issues)
venv/bin/pip install -q fastapi uvicorn numpy joblib requests boto3 python-dotenv

# ---------- Federated Aggregator ----------
cat > ai/federation/aggregator.py <<'EOF'
import os, json, time, joblib
from typing import Dict, Any

META_PATH = "models/federated_meta.json"
MODEL_PATH = "models/federated_model.pkl"

def _load_meta() -> Dict[str, Any]:
    if os.path.exists(META_PATH):
        return json.load(open(META_PATH))
    return {"peers": {}, "best_score": -1e9, "last_update": None}

def _save_meta(meta: Dict[str, Any]): json.dump(meta, open(META_PATH, "w"))

def accept_update(peer_id: str, score: float, weights: Dict[str, float]):
    os.makedirs("models", exist_ok=True)
    meta = _load_meta()
    meta["peers"][peer_id] = {"score": score, "ts": time.time()}
    if score >= meta.get("best_score", -1e9):
        joblib.dump({"weights": weights, "score": score, "peer": peer_id, "ts": time.time()}, MODEL_PATH)
        meta["best_score"] = score
        meta["last_update"] = time.time()
    _save_meta(meta)
    return {"ok": True, "best_score": meta["best_score"], "peers": len(meta["peers"])}

def best_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return {"weights": {"w": 0.0}, "score": 0.0, "peer": "none", "ts": 0}
EOF

# ---------- Genetic Trainer ----------
cat > ai/genetic/trainer.py <<'EOF'
import random, joblib, os, time

GA_PATH = "models/ga_model.pkl"

def _fitness(weights):
    # Toy fitness: prefer small positive weight
    w = float(weights.get("w", 0.0))
    return 1.0 - abs(w - 0.2)

def evolve(pop_size=16, gens=8, mutate=0.1):
    pop = [{"w": random.uniform(-1, 1)} for _ in range(pop_size)]
    for _ in range(gens):
        scored = [(w, _fitness(w)) for w in pop]
        scored.sort(key=lambda x: x[1], reverse=True)
        keep = [w for w, _ in scored[: max(2, pop_size // 2)]]
        children = []
        while len(keep) + len(children) < pop_size:
            a, b = random.sample(keep, 2)
            child = {"w": (a["w"] + b["w"]) / 2.0}
            if random.random() < mutate:
                child["w"] += random.uniform(-0.1, 0.1)
            children.append(child)
        pop = keep + children
    best = max(pop, key=_fitness)
    os.makedirs("models", exist_ok=True)
    joblib.dump({"weights": best, "score": _fitness(best), "ts": time.time()}, GA_PATH)
    return {"best": best, "score": _fitness(best), "path": GA_PATH}
EOF

# ---------- Voice Command (file-driven, no mic needed) ----------
cat > tools/voice_command_daemon.py <<'EOF'
import os, time, json, requests

CMD_FILE = "voice_commands.txt"   # put lines like: set_strategy B  | pause | resume
BASE = os.environ.get("AIMW_BASE", "http://127.0.0.1:8000")

def _apply(cmd: str):
    c = cmd.strip().lower()
    if not c: return "skip"
    if c.startswith("set_strategy"):
        _, s = c.split()
        requests.post(f"{BASE}/api/strategy", json={"strategy": s.upper()}, timeout=2)
        return f"set_strategy {s}"
    if c == "pause":
        requests.post(f"{BASE}/api/mode", json={"mode": "paused"}, timeout=2)
        return "paused"
    if c == "resume":
        requests.post(f"{BASE}/api/mode", json={"mode": "trading"}, timeout=2)
        return "trading"
    if c.startswith("risk_cap"):
        _, val = c.split()
        requests.post(f"{BASE}/api/risk", json={"cap": float(val)}, timeout=2)
        return f"risk_cap {val}"
    return f"unknown:{c}"

def main():
    seen = set()
    while True:
        if os.path.exists(CMD_FILE):
            with open(CMD_FILE) as f:
                for i, line in enumerate(f):
                    if i in seen: continue
                    action = _apply(line)
                    print("🎙️ voice:", action)
                    seen.add(i)
        time.sleep(2)

if __name__ == "__main__":
    main()
EOF

# ---------- main.py (global) ----------
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv; load_dotenv()
import os, asyncio, random, time
from ai.brokers.router import account_equity_cash, submit_market
from ai.strategy_manager import pick as pick_strategy
from ai.risk.var_calc import value_at_risk
from ai.sentiment.feed import sentiment_boost
from ai.federation.aggregator import accept_update, best_model
from ai.genetic.trainer import evolve

app = FastAPI(title="AI Money Web :: Federated Global (83–90)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

MODE = {"mode": "trading"}
RISK = {"cap": 0.03}    # VaR cap
HIST = {"eq": []}

@app.get("/")
def root(): return {"message": "✅ Global engine online (83–90)", "mode": MODE["mode"], "risk_cap": RISK["cap"]}

@app.post("/api/mode")
def set_mode(payload: dict = Body(...)):
    MODE["mode"] = payload.get("mode", "trading")
    return {"ok": True, "mode": MODE["mode"]}

@app.post("/api/risk")
def set_risk(payload: dict = Body(...)):
    RISK["cap"] = float(payload.get("cap", 0.03))
    return {"ok": True, "cap": RISK["cap"]}

@app.post("/api/federate")
def federate(payload: dict = Body(...)):
    peer = payload.get("peer", "unknown")
    score = float(payload.get("score", 0.0))
    weights = payload.get("weights", {"w": 0})
    return accept_update(peer, score, weights)

@app.get("/api/federate/best")
def federate_best(): return best_model()

@app.post("/api/genetic/train")
def ga_train():
    res = evolve()
    # push update into federation immediately
    return accept_update("local_ga", float(res["score"]), res["best"])

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(open("static/dashboard.html").read())

@app.websocket("/ws/global")
async def ws_global(ws: WebSocket):
    await ws.accept()
    while True:
        eq, ca = account_equity_cash()
        HIST["eq"].append(eq)
        pnl = (eq - 100000) / 100000
        var = value_at_risk([pnl])
        sent = sentiment_boost("AAPL")
        base_sig = pick_strategy(pnl, abs(pnl) + 0.01)
        bm = best_model()
        w = float(bm.get("weights", {}).get("w", 0.0))
        fed_sig = base_sig + (0.25 * w) + (0.1 * sent)
        if MODE["mode"] != "trading": action = "hold"
        elif var > RISK["cap"]: action = "hold"
        else: action = "buy" if fed_sig > 0 else "sell"
        if action != "hold": submit_market("AAPL", action, 1)
        await ws.send_json({
            "equity": eq, "signal": fed_sig, "action": action,
            "var": var, "cap": RISK["cap"], "sentiment": sent,
            "mode": MODE["mode"], "w": w, "peers": "federated"
        })
        await asyncio.sleep(5)
EOF

# ---------- Dashboard ----------
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>🚀 AI Money Web Global (83–90)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#000;color:#0ff;font-family:monospace;text-align:center}
.pill{display:inline-block;margin:.25rem;padding:.2rem .6rem;border:1px solid #0ff;border-radius:9999px}
canvas{width:92%;max-width:1100px;margin:auto}
</style></head><body>
<h1>🌍 AI Money Web — Federated Global (83–90)</h1>
<div id="tags">
  <span class="pill" id="mode">mode: —</span>
  <span class="pill" id="cap">cap: —</span>
  <span class="pill" id="w">w: —</span>
</div>
<div id="status">Connecting…</div>
<canvas id="chart"></canvas>
<script>
const modeEl=document.getElementById('mode'), capEl=document.getElementById('cap'), wEl=document.getElementById('w');
const ctx=document.getElementById('chart').getContext('2d');
const chart=new Chart(ctx,{type:'line',data:{labels:[],datasets:[
{label:'Equity',borderColor:'#0ff',data:[]},
{label:'Signal',borderColor:'#ff0',data:[]},
{label:'VaR',borderColor:'#f00',data:[],yAxisID:'y1'}]},
options:{scales:{y1:{position:'right'}}}});
const ws=new WebSocket('ws://127.0.0.1:8000/ws/global');
ws.onmessage=(e)=>{
  const d=JSON.parse(e.data);
  document.getElementById('status').textContent=`Eq:${d.equity.toFixed(2)} | Sig:${d.signal.toFixed(3)} | Var:${d.var.toFixed(3)} | Act:${d.action}`;
  modeEl.textContent='mode: '+d.mode; capEl.textContent='cap: '+d.cap.toFixed(3); wEl.textContent='w: '+d.w.toFixed(3);
  chart.data.labels.push(new Date().toLocaleTimeString());
  chart.data.datasets[0].data.push(d.equity);
  chart.data.datasets[1].data.push(d.signal);
  chart.data.datasets[2].data.push(d.var);
  if(chart.data.labels.length>100){chart.data.labels.shift();chart.data.datasets.forEach(ds=>ds.data.shift());}
  chart.update();
};
</script></body></html>
EOF

# ---------- Launch ----------
chmod +x *.sh tools/*.py ai/*.py || true
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5
open http://127.0.0.1:8000/dashboard || true

echo "🎯 Phase 83–90 complete — federated + GA + voice (file) live."
echo ""
echo "📄 Voice control: add lines to ./voice_commands.txt then run:"
echo "   nohup venv/bin/python3 tools/voice_command_daemon.py > logs/voice.log 2>&1 &"
echo "   Examples:"
echo "     set_strategy B"
echo "     pause"
echo "     resume"
echo "     risk_cap 0.025"

