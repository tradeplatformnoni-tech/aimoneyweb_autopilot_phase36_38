#!/bin/zsh
echo "🚀 Phase 161–170 :: Helm + Istio + Argo Autopilot Setup..."

# 1️⃣ Safety Backup
timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static helm charts tools
cp main.py backups/main.py.$timestamp.bak 2>/dev/null || true
echo "✅ Backup complete -> backups/main.py.$timestamp.bak"

# 2️⃣ Rebuild main.py
cat > main.py << 'EOF'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import asyncio, os, datetime

app = FastAPI(title="AI Money Web Autopilot v161–170")

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
        "message": "✅ Helm + Argo Autopilot Online",
        "phase": "161–170",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/api/alpaca_status")
def alpaca_status():
    return {"status": "connected", "equity": 100000, "cash": 25000}

@app.websocket("/ws/alpaca_status")
async def ws_alpaca_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "status": "connected",
                "equity": 100000,
                "cash": 25000,
                "phase": "161–170",
                "update": "live"
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        print("🔌 Client disconnected / ws/alpaca_status")
EOF

# 3️⃣ Create dashboard.html
cat > static/dashboard.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>AI Money Web v161–170</title>
  <style>
    body {font-family: Arial; background:#0b0c10; color:#eee; text-align:center; padding:40px;}
    .status {color:#0f0; font-weight:bold;}
    canvas {background:#1f2833; margin-top:20px;}
  </style>
</head>
<body>
  <h1>🚀 AI Money Web Autopilot Dashboard (Phase 161–170)</h1>
  <div id="status" class="status">Connecting to server...</div>
  <canvas id="chart" width="600" height="250"></canvas>

  <script>
  const ws = new WebSocket("ws://127.0.0.1:8000/ws/alpaca_status");
  ws.onmessage = e => {
      const d = JSON.parse(e.data);
      document.getElementById("status").textContent =
          "📡 " + d.status + " | Equity: $" + d.equity + " | Cash: $" + d.cash;
  };
  ws.onclose = () => { document.getElementById("status").textContent = "❌ Disconnected"; };
  </script>
</body>
</html>
EOF

# 4️⃣ Create Helm chart
mkdir -p helm/aimoneyweb/templates
cat > helm/aimoneyweb/Chart.yaml << 'EOF'
apiVersion: v2
name: aimoneyweb
version: 0.1.0
appVersion: "161-170"
EOF

cat > helm/aimoneyweb/values.yaml << 'EOF'
image:
  repository: ghcr.io/tradeplatformnoni-tech/aimoneyweb
  tag: latest
service:
  port: 8000
EOF

cat > helm/aimoneyweb/templates/deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aimoneyweb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aimoneyweb
  template:
    metadata:
      labels:
        app: aimoneyweb
    spec:
      containers:
      - name: aimoneyweb
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: {{ .Values.service.port }}
---
apiVersion: v1
kind: Service
metadata:
  name: aimoneyweb
spec:
  type: ClusterIP
  selector:
    app: aimoneyweb
  ports:
  - port: 8000
    targetPort: 8000
EOF

# 5️⃣ Self-healing watcher
cat > tools/autopilot_watcher.py << 'EOF'
import os, time, subprocess, requests
PORT = 8000
def health(): 
    try: return requests.get(f"http://127.0.0.1:{PORT}/").ok
    except Exception: return False
def main():
    while True:
        if not health():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",str(PORT)])
        time.sleep(10)
if __name__ == "__main__": main()
EOF

# 6️⃣ Helm + Argo manifest
mkdir -p k8s
cat > k8s/argoapp.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: aimoneyweb
spec:
  project: default
  source:
    repoURL: 'https://github.com/tradeplatformnoni-tech/aimoneyweb_autopilot_phase36_38.git'
    path: helm/aimoneyweb
    targetRevision: main
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: aimoney
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF

# 7️⃣ Make scripts executable
chmod +x tools/*.py || true

# 8️⃣ Launch backend + watcher
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
nohup venv/bin/python3 tools/autopilot_watcher.py > logs/watcher.log 2>&1 &
sleep 5

# 9️⃣ Check
if curl -s http://127.0.0.1:8000/ | grep -q "Helm"; then
  echo "✅ Backend healthy. Open dashboard:"
  open http://127.0.0.1:8000/dashboard
else
  echo "❌ Backend not responding. See logs/backend.log"
fi

echo "🎯 Phase 161–170 Autopilot Deployment Complete."
echo "💾 Logs → ./logs/backend.log"

