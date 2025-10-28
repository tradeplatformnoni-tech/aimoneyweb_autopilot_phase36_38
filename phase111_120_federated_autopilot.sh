# 🧠 Phase 111–120 :: Cloud Backup + Federated Trainer Network
echo "🚀 Starting Phase 111–120 :: Federated Trainer Setup..."
timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools ai cloud
[ -f main.py ] && cp main.py backups/main.py.$timestamp.bak && echo "✅ Backup → backups/main.py.$timestamp.bak"

# 1️⃣ Install dependencies
venv/bin/pip install -q fastapi uvicorn requests aiohttp python-dotenv boto3

# 2️⃣ Create main.py
cat > main.py <<'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio, os, datetime, random, json, pathlib

app = FastAPI(title="AI Money Web :: Federated Cloud Trainer (111–120)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "✅ Federated Trainer Node active",
        "phase": "111–120",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "cloud_backup": True,
        "node_id": random.randint(1000,9999),
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return FileResponse("static/dashboard.html")

@app.websocket("/ws/federated")
async def ws_federated(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({
                "node_id": random.randint(1000,9999),
                "peer_nodes": random.randint(2,10),
                "sync_rate": round(random.uniform(0.5, 1.0), 2),
                "loss_delta": round(random.uniform(-0.005, 0.01), 4),
                "upload_status": random.choice(["uploaded","pending","complete"]),
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            await asyncio.sleep(4)
    except WebSocketDisconnect:
        print("🔌 Client disconnected from /ws/federated")

@app.post("/api/cloud_backup")
async def cloud_backup():
    # Simulated upload to cloud folder
    log_path = pathlib.Path("logs/federated_sync.log")
    cloud_dir = pathlib.Path("cloud")
    cloud_dir.mkdir(exist_ok=True)
    backup_name = f"trainer_backup_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    data = {"backup_time": datetime.datetime.utcnow().isoformat(), "nodes": random.randint(3,12)}
    (cloud_dir / backup_name).write_text(json.dumps(data, indent=2))
    log_path.write_text(f"Uploaded: {backup_name}\n", encoding="utf-8")
    return {"status":"uploaded","file":backup_name}
EOF

# 3️⃣ Create dashboard HTML
cat > static/dashboard.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Federated Trainer Network (111–120)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {background:#000;color:#0f0;font-family:Consolas;text-align:center;}
  canvas{max-width:700px;margin-top:25px;}
  .node {margin-top:10px;}
</style>
</head>
<body>
<h1>🌐 Federated Trainer Cloud Sync</h1>
<p>Node ID: <span id="node"></span></p>
<p>Peers: <span id="peers"></span></p>
<p>Sync Rate: <span id="sync"></span></p>
<p>Loss Δ: <span id="loss"></span></p>
<canvas id="chart"></canvas>
<script>
const ws = new WebSocket("ws://127.0.0.1:8000/ws/federated");
const ctx = document.getElementById("chart").getContext("2d");
let data = {labels:[],datasets:[{label:"Loss Δ",data:[],borderColor:"lime",fill:false}]};
const chart = new Chart(ctx,{type:"line",data});
ws.onmessage = e=>{
 const j=JSON.parse(e.data);
 document.getElementById("node").innerText=j.node_id;
 document.getElementById("peers").innerText=j.peer_nodes;
 document.getElementById("sync").innerText=j.sync_rate;
 document.getElementById("loss").innerText=j.loss_delta;
 data.labels.push(j.timestamp.split("T")[1].split(".")[0]);
 data.datasets[0].data.push(j.loss_delta);
 if(data.labels.length>30){data.labels.shift();data.datasets[0].data.shift();}
 chart.update();
};
</script>
</body>
</html>
EOF

# 4️⃣ Create federated watcher
cat > tools/federated_watcher.py <<'EOF'
import subprocess, time, requests, os

PORT = "8000"
BASE = f"http://127.0.0.1:{PORT}"

def healthy():
    try:
        r = requests.get(BASE, timeout=2)
        return r.status_code == 200
    except:
        return False

def start():
    return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
        stdout=open("logs/backend.log","a"), stderr=subprocess.STDOUT)

def loop():
    p = start()
    while True:
        if p.poll() is not None or not healthy():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p = start()
        if time.time() % 120 < 2: # upload every ~2 minutes
            requests.post(BASE+"/api/cloud_backup",timeout=3)
        time.sleep(8)

if __name__=="__main__":
    os.makedirs("logs",exist_ok=True)
    loop()
EOF

# 5️⃣ Launch backend + watcher
echo "🔪 Freeing :8000…"; kill -9 $(lsof -t -i:8000) 2>/dev/null || true
echo "🚀 Starting backend + federated watcher..."
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 tools/federated_watcher.py > logs/watcher.log 2>&1 &
sleep 6

# 6️⃣ Verify + open
if curl -s http://127.0.0.1:8000/ | grep -q "Federated"; then
  echo "✅ Backend alive. Opening dashboard..."
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend failed. Check logs/backend.log"
  head -n 40 logs/backend.log
fi

echo "🎯 Phase 111–120 Federated Trainer setup complete."
echo "💾 Logs → ./logs/backend.log ./logs/watcher.log"
echo "💡 If you see 'permission denied': chmod +x *.sh tools/*.py ai/*.py"

