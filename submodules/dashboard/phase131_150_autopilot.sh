# 🧠 Phase 131–150 :: Optimizer + Edge Mesh + Safety + Compliance
echo "🚀 Starting Phase 131–150 Autopilot…"

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools ai/optimizer ai/safety ai/mesh audit exports

# 0) Backup
[ -f main.py ] && cp main.py "backups/main.py.$timestamp.bak" && echo "✅ Backup → backups/main.py.$timestamp.bak"

# 1) Deps
venv/bin/pip install -q fastapi uvicorn requests python-dotenv numpy

# 2) Optimizer stubs (Bayesian-ish search, canary, chaos, kill-switch, edge mesh)
cat > ai/optimizer/bayes.py <<'PY'
import random
class BayesOptimizer:
    def __init__(self):
        self.best_score=-1e9
        self.best_params={"alpha":0.5,"beta":0.5}
    def suggest(self):
        # explore around current best
        a=max(0.0,min(1.0,self.best_params["alpha"]+random.uniform(-0.1,0.1)))
        b=max(0.0,min(1.0,self.best_params["beta"]+random.uniform(-0.1,0.1)))
        return {"alpha":a,"beta":b}
    def observe(self,params,score):
        if score>self.best_score:
            self.best_score=score
            self.best_params=params
    def status(self):
        return {"best_score":self.best_score,"best_params":self.best_params}
PY

cat > ai/mesh/edge_mesh.py <<'PY'
import random,time
def edge_heartbeat():
    # pretend 3-8 edge nodes are alive, some lagging
    return {
        "nodes": random.randint(3,8),
        "avg_latency_ms": round(random.uniform(20,120),1),
        "lagging": random.randint(0,2)
    }
PY

cat > ai/optimizer/canary.py <<'PY'
def is_canary_good(metrics):
    # accept if recent pnl positive and latency reasonable
    return (metrics.get("pnl",0)>0) and (metrics.get("latency_ms",100)<150)
PY

cat > ai/safety/kill_switch.py <<'PY'
def tripped(pnl_pct, max_drawdown_pct, var_est):
    # kill if >5% dd or VaR > 3% or pnl below -2% intraday
    return (max_drawdown_pct<=-0.05) or (var_est>0.03) or (pnl_pct<-0.02)
PY

cat > ai/safety/chaos.py <<'PY'
import random
def maybe_fault():
    # inject 10% chance of mild fault signal (for resilience drills)
    return random.random()<0.10
PY

# 3) Main API
cat > main.py <<'PY'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from dotenv import load_dotenv; load_dotenv()
import asyncio, os, json, time, random, datetime, pathlib

from ai.optimizer.bayes import BayesOptimizer
from ai.optimizer.canary import is_canary_good
from ai.safety.kill_switch import tripped
from ai.safety.chaos import maybe_fault
from ai.mesh.edge_mesh import edge_heartbeat

app = FastAPI(title="AI Money Web :: Optimizer & Safety (131–150)")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

STATE = {
    "mode":"trading",
    "risk_cap":0.03,
    "pnl_pct":0.0,
    "max_dd_pct":0.0,
    "var_est":0.01,
    "equity":100000.0
}
OPT = BayesOptimizer()
AUDIT_DIR = pathlib.Path("audit"); AUDIT_DIR.mkdir(exist_ok=True)

def audit(event, payload):
    rec = {"ts":datetime.datetime.utcnow().isoformat(),"event":event,"payload":payload}
    with open(AUDIT_DIR/"events.jsonl","a") as f:
        f.write(json.dumps(rec)+"\n")

@app.get("/")
def root():
    return {"message":"✅ Optimizer & Safety online","phase":"131–150","mode":STATE["mode"],"risk_cap":STATE["risk_cap"]}

@app.get("/dashboard",response_class=HTMLResponse)
def dashboard():
    return FileResponse("static/dashboard.html")

@app.post("/api/pause")
def pause():
    STATE["mode"]="paused"; audit("pause",{})
    return {"ok":True,"mode":STATE["mode"]}

@app.post("/api/resume")
def resume():
    STATE["mode"]="trading"; audit("resume",{})
    return {"ok":True,"mode":STATE["mode"]}

@app.get("/api/export_audit")
def export_audit():
    src = AUDIT_DIR/"events.jsonl"
    if not src.exists():
        return JSONResponse({"ok":True,"file":None})
    dst = pathlib.Path("exports")/f"audit_{int(time.time())}.jsonl"
    dst.write_text(src.read_text())
    return {"ok":True,"file":str(dst)}

@app.websocket("/ws/optimizer")
async def ws_optimizer(ws:WebSocket):
    await ws.accept()
    try:
        wins, losses = 0, 0
        dd_min = 0.0
        while True:
            # chaos testing
            fault = maybe_fault()
            # simulate market/equity
            shock = random.uniform(-300,300) * (1.5 if fault else 1.0)
            STATE["equity"] = max(50000.0, STATE["equity"] + shock)
            pnl = STATE["equity"] - 100000.0
            STATE["pnl_pct"] = pnl/100000.0
            dd_min = min(dd_min, STATE["pnl_pct"])
            STATE["max_dd_pct"] = dd_min
            STATE["var_est"] = max(0.005, min(0.05, abs(STATE["pnl_pct"])*0.8))

            # optimizer step
            params = OPT.suggest()
            score = (STATE["pnl_pct"] - abs(STATE["var_est"])*0.5) - (0.01 if fault else 0.0)
            OPT.observe(params, score)
            kpis = OPT.status()

            # canary + kill switch
            canary_ok = is_canary_good({"pnl":pnl,"latency_ms":random.uniform(25,140)})
            kill = tripped(STATE["pnl_pct"], STATE["max_dd_pct"], STATE["var_est"])
            if kill: STATE["mode"]="paused"

            # record audit
            audit("tick",{"pnl_pct":STATE["pnl_pct"],"dd_pct":STATE["max_dd_pct"],"var":STATE["var_est"],"params":params,"score":score,"fault":fault,"canary":canary_ok,"kill":kill})

            # edge mesh heartbeat
            mesh = edge_heartbeat()

            await ws.send_json({
                "equity": round(STATE["equity"],2),
                "pnl_pct": round(STATE["pnl_pct"],4),
                "max_dd_pct": round(STATE["max_dd_pct"],4),
                "var_est": round(STATE["var_est"],4),
                "mode": STATE["mode"],
                "optimizer": kpis,
                "params": params,
                "canary_ok": canary_ok,
                "fault_injected": fault,
                "mesh": mesh,
                "ts": datetime.datetime.utcnow().isoformat()
            })
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        print("🔌 WS disconnected")
PY

# 4) Dashboard (Pro dark skin + KPIs)
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>⚙️ AI Optimizer & Safety (131–150)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
 body{background:#0b0f14;color:#e6f3ff;font-family:Inter,system-ui,Arial;margin:0;padding:24px}
 h1{margin:0 0 8px;font-weight:700}
 .row{display:flex;gap:16px;flex-wrap:wrap}
 .card{background:#101826;border:1px solid #223146;border-radius:12px;padding:16px;flex:1;min-width:260px}
 .kpi{font-size:14px;margin:4px 0}
 canvas{max-width:1100px;width:100%;height:360px}
 .ok{color:#6af58b}.bad{color:#ff6a6a}
</style></head><body>
<h1>⚙️ AI Optimizer & Safety (131–150)</h1>
<div class="row">
  <div class="card">
    <div class="kpi">Mode: <span id="mode">…</span></div>
    <div class="kpi">Equity: <span id="equity">…</span></div>
    <div class="kpi">PnL %: <span id="pnl">…</span></div>
    <div class="kpi">Max DD %: <span id="dd">…</span></div>
    <div class="kpi">VaR: <span id="var">…</span></div>
    <div class="kpi">Canary: <span id="canary">…</span></div>
    <div class="kpi">Fault: <span id="fault">…</span></div>
    <div class="kpi">Mesh: <span id="mesh">…</span></div>
  </div>
  <div class="card">
    <div class="kpi">Best Score: <span id="bestScore">…</span></div>
    <div class="kpi">Best Params: <span id="bestParams">…</span></div>
    <div class="kpi">Current Params: <span id="curParams">…</span></div>
    <button id="pauseBtn">Pause</button>
    <button id="resumeBtn">Resume</button>
    <button id="exportBtn">Export Audit</button>
  </div>
</div>
<div class="card" style="margin-top:16px">
  <canvas id="equityChart"></canvas>
</div>
<script>
const ws=new WebSocket("ws://127.0.0.1:8000/ws/optimizer");
const ctx=document.getElementById("equityChart").getContext("2d");
const chart=new Chart(ctx,{type:"line",data:{labels:[],datasets:[
 {label:"Equity",data:[],borderColor:"#6af58b",fill:false},
 {label:"VaR",data:[],borderColor:"#8bb9ff",fill:false,yAxisID:"y1"},
 {label:"PnL %",data:[],borderColor:"#ffd36a",fill:false,yAxisID:"y2"},
]},options:{scales:{y1:{position:"right"},y2:{position:"right"}}});
function pushPoint(lbl,eq,var_,pnl){
  chart.data.labels.push(lbl);
  chart.data.datasets[0].data.push(eq);
  chart.data.datasets[1].data.push(var_);
  chart.data.datasets[2].data.push(pnl);
  if(chart.data.labels.length>120){chart.data.labels.shift();chart.data.datasets.forEach(d=>d.data.shift());}
  chart.update();
}
ws.onmessage=(e)=>{
  const d=JSON.parse(e.data);
  document.getElementById("mode").textContent=d.mode;
  document.getElementById("equity").textContent=d.equity.toFixed(2);
  document.getElementById("pnl").textContent=d.pnl_pct.toFixed(4);
  document.getElementById("dd").textContent=d.max_dd_pct.toFixed(4);
  document.getElementById("var").textContent=d.var_est.toFixed(4);
  document.getElementById("canary").innerHTML=d.canary_ok?'<span class="ok">OK</span>':'<span class="bad">FAIL</span>';
  document.getElementById("fault").innerHTML=d.fault_injected?'<span class="bad">YES</span>':'NO';
  document.getElementById("mesh").textContent=`nodes=${d.mesh.nodes}, lag=${d.mesh.lagging}, latency=${d.mesh.avg_latency_ms}ms`;
  document.getElementById("bestScore").textContent=d.optimizer.best_score.toFixed(6);
  document.getElementById("bestParams").textContent=JSON.stringify(d.optimizer.best_params);
  document.getElementById("curParams").textContent=JSON.stringify(d.params);
  pushPoint(d.ts.split("T")[1].split(".")[0], d.equity, d.var_est, d.pnl_pct);
};
document.getElementById("pauseBtn").onclick=()=>fetch("/api/pause",{method:"POST"});
document.getElementById("resumeBtn").onclick=()=>fetch("/api/resume",{method:"POST"});
document.getElementById("exportBtn").onclick=()=>fetch("/api/export_audit").then(r=>r.json()).then(j=>alert("Exported: "+j.file));
</script>
</body></html>
HTML

# 5) Watcher (auto-heal)
cat > tools/optimizer_watcher.py <<'PY'
import subprocess, time, requests, os
PORT="8000"; BASE=f"http://127.0.0.1:{PORT}"
def start():
    return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
        stdout=open("logs/backend.log","a"), stderr=subprocess.STDOUT)
def ok():
    try: return requests.get(BASE,timeout=2).status_code==200
    except: return False
def loop():
    p=start()
    while True:
        if p.poll() is not None or not ok():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p=start()
        time.sleep(7)
if __name__=="__main__":
    os.makedirs("logs",exist_ok=True); loop()
PY

# 6) Launch
echo "🔪 Freeing :8000…"; kill -9 $(lsof -t -i:8000) 2>/dev/null || true
echo "🚀 Starting backend + watcher…"
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 tools/optimizer_watcher.py > logs/watcher.log 2>&1 &
sleep 5

# 7) Verify + Open
if curl -s http://127.0.0.1:8000/ | grep -q "Optimizer"; then
  echo "✅ Backend alive. Opening dashboard…"
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend failed. See logs/backend.log"
  head -n 60 logs/backend.log || true
fi

echo "🎯 Phase 131–150 complete. Logs → ./logs/backend.log ./logs/watcher.log"
echo "🛠 If macOS says 'permission denied':  chmod +x *.sh tools/*.py ai/*.py"

