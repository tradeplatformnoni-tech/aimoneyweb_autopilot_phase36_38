# 🧠 Phase 151–160 :: Kubernetes + Canary + GitOps CI (One-Shot)
echo "🚀 Phase 151–160 :: Kubernetes + Canary + GitOps CI bootstrap…"

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static tools k8s .github/workflows

# 0) Backup
[ -f main.py ] && cp main.py "backups/main.py.$timestamp.bak" && echo "✅ Backup → backups/main.py.$timestamp.bak"

# 1) Ensure deps (local dev)
venv/bin/pip install -q fastapi uvicorn requests python-dotenv

# 2) Production main.py (simple, fast, reliable)
cat > main.py <<'PY'
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio, datetime, random

app = FastAPI(title="AI Money Web :: K8s Canary (151–160)")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {
        "message": "✅ K8s Canary service online",
        "phase": "151–160",
        "version": "v1",  # override at build with ARG/ENV if desired
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return FileResponse("static/dashboard.html")

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({
                "equity": round(100000 + random.uniform(-400, 400), 2),
                "var": round(random.uniform(0.005, 0.035), 4),
                "signal": random.choice(["BUY","SELL","HOLD"]),
                "ts": datetime.datetime.utcnow().isoformat()
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
PY

# 3) Dashboard (compact)
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>AI Money Web :: K8s Canary (151–160)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
 body{background:#0d1117;color:#fff;font-family:system-ui;margin:0;padding:24px}
 h1{margin:0 0 8px;color:#00ffc8}
 canvas{max-width:960px;width:100%;height:360px}
 .row{display:flex;gap:16px;flex-wrap:wrap}
 .card{background:#111826;border:1px solid #223146;border-radius:12px;padding:16px;flex:1;min-width:260px}
</style></head>
<body>
<h1>🚀 AI Money Web :: K8s Canary</h1>
<div class="row">
  <div class="card">
    <div>Status: <span id="status">Connecting…</span></div>
    <div>Signal: <span id="signal">—</span></div>
    <div>VaR: <span id="var">—</span></div>
  </div>
</div>
<canvas id="chart"></canvas>
<script>
const ws=new WebSocket("ws://"+location.host+"/ws/live");
const ctx=document.getElementById("chart").getContext("2d");
const data={labels:[],datasets:[{label:"Equity",data:[],borderColor:"#00ffc8",fill:false}]};
const chart=new Chart(ctx,{type:"line",data});
ws.onmessage=e=>{
 const j=JSON.parse(e.data);
 document.getElementById("status").innerText="OK";
 document.getElementById("signal").innerText=j.signal;
 document.getElementById("var").innerText=j.var;
 data.labels.push(j.ts.split("T")[1].split(".")[0]);
 data.datasets[0].data.push(j.equity);
 if(data.labels.length>120){data.labels.shift();data.datasets[0].data.shift();}
 chart.update();
};
</script></body></html>
HTML

# 4) Dockerfile + compose (for local sanity)
cat > Dockerfile <<'DOCK'
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
EXPOSE 8000
CMD ["python","-m","uvicorn","main:app","--host","0.0.0.0","--port","8000"]
DOCK

cat > requirements.txt <<'REQ'
fastapi
uvicorn
requests
python-dotenv
REQ

cat > docker-compose.yml <<'YML'
version: "3.8"
services:
  aimoneyweb:
    build: .
    ports: ["8000:8000"]
    environment:
      - PORT=8000
    restart: unless-stopped
YML

# 5) K8s manifests (namespace, config, stable+canary, service, ingress)
cat > k8s/namespace.yaml <<'YML'
apiVersion: v1
kind: Namespace
metadata:
  name: aimoney
YML

cat > k8s/configmap.yaml <<'YML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: aimoneyweb-config
  namespace: aimoney
data:
  APP_NAME: "AI Money Web"
  PHASE: "151-160"
YML

# Stable deployment (v1)
cat > k8s/deploy-stable.yaml <<'YML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aimoneyweb-stable
  namespace: aimoney
spec:
  replicas: 4
  selector:
    matchLabels:
      app: aimoneyweb
      track: stable
  template:
    metadata:
      labels:
        app: aimoneyweb
        track: stable
    spec:
      containers:
      - name: app
        image: ghcr.io/OWNER/aimoneyweb:stable
        imagePullPolicy: IfNotPresent
        env:
        - name: PORT
          value: "8000"
        ports:
        - containerPort: 8000
        readinessProbe:
          httpGet: { path: "/", port: 8000 }
          initialDelaySeconds: 3
          periodSeconds: 5
        livenessProbe:
          httpGet: { path: "/", port: 8000 }
          initialDelaySeconds: 10
          periodSeconds: 10
YML

# Canary deployment (v2) – lower replicas to weight traffic
cat > k8s/deploy-canary.yaml <<'YML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aimoneyweb-canary
  namespace: aimoney
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aimoneyweb
      track: canary
  template:
    metadata:
      labels:
        app: aimoneyweb
        track: canary
    spec:
      containers:
      - name: app
        image: ghcr.io/OWNER/aimoneyweb:canary
        imagePullPolicy: IfNotPresent
        env:
        - name: PORT
          value: "8000"
        ports:
        - containerPort: 8000
        readinessProbe:
          httpGet: { path: "/", port: 8000 }
          initialDelaySeconds: 3
          periodSeconds: 5
        livenessProbe:
          httpGet: { path: "/", port: 8000 }
          initialDelaySeconds: 10
          periodSeconds: 10
YML

# One Service across both (K8s will round-robin across all ready pods)
cat > k8s/service.yaml <<'YML'
apiVersion: v1
kind: Service
metadata:
  name: aimoneyweb-svc
  namespace: aimoney
spec:
  selector:
    app: aimoneyweb
  ports:
  - name: http
    port: 80
    targetPort: 8000
  type: ClusterIP
YML

# Minimal Ingress (assumes an Ingress Controller is installed; edit host)
cat > k8s/ingress.yaml <<'YML'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aimoneyweb-ingress
  namespace: aimoney
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
  - host: aimoney.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aimoneyweb-svc
            port:
              number: 80
YML

# 6) GitHub Actions (GitOps-style build & deploy)
mkdir -p .github/workflows
cat > .github/workflows/cd.yaml <<'YML'
name: Build & Deploy (K8s Canary)
on:
  push:
    branches: [ "main" ]
    paths: ["**/*.py","Dockerfile","requirements.txt","static/**","k8s/**",".github/workflows/**"]
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-buildx-action@v3
    - name: Login GHCR
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    - name: Build images
      run: |
        IMAGE=ghcr.io/${{ github.repository_owner }}/aimoneyweb
        docker build -t $IMAGE:stable .
        docker tag $IMAGE:stable $IMAGE:canary
        docker push $IMAGE:stable
        docker push $IMAGE:canary
    - name: Upload k8s manifests (artifact)
      uses: actions/upload-artifact@v4
      with:
        name: k8s-manifests
        path: k8s/
  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
    - uses: actions/download-artifact@v4
      with:
        name: k8s-manifests
        path: k8s
    - name: Setup kubectl
      uses: azure/setup-kubectl@v4
      with:
        version: 'v1.30.0'
    - name: Kubeconfig
      run: |
        mkdir -p ~/.kube
        echo "${KUBECONFIG_CONTENT}" > ~/.kube/config
      env:
        KUBECONFIG_CONTENT: ${{ secrets.KUBECONFIG_CONTENT }}
    - name: Apply manifests
      run: |
        kubectl apply -f k8s/namespace.yaml
        kubectl apply -f k8s/configmap.yaml
        kubectl apply -f k8s/deploy-stable.yaml
        kubectl apply -f k8s/deploy-canary.yaml
        kubectl apply -f k8s/service.yaml
        kubectl apply -f k8s/ingress.yaml
YML

# 7) Local helpers: k8s deploy + quick-fix launcher
cat > tools/k8s_deploy_local.sh <<'SH'
#!/bin/zsh
set -e
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deploy-stable.yaml
kubectl apply -f k8s/deploy-canary.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
echo "✅ Applied. Use: kubectl -n aimoney get pods,svc,ingress"
SH
chmod +x tools/k8s_deploy_local.sh

cat > tools/phase151_160_quickfix.sh <<'SH'
#!/bin/zsh
set -e
echo "🧩 QuickFix :: kill & relaunch local server"
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
open http://127.0.0.1:8000/dashboard || true
echo "✅ Done. Logs → logs/backend.log"
SH
chmod +x tools/phase151_160_quickfix.sh

# 8) Make everything executable and print next steps
chmod +x *.sh tools/*.sh tools/*.py || true

echo ""
echo "🎯 Phase 151–160 ready!"
echo "————————————————————————————————————————————————————————————"
echo "LOCAL TEST:"
echo "  docker compose up --build -d"
echo "  open http://127.0.0.1:8000/dashboard"
echo ""
echo "QUICK-FIX RELAUNCH (local uvicorn):"
echo "  ./tools/phase151_160_quickfix.sh"
echo ""
echo "K8S DEPLOY (requires kubeconfig):"
echo "  ./tools/k8s_deploy_local.sh"
echo "  kubectl -n aimoney get pods,svc,ingress"
echo ""
echo "GITHUB ACTIONS (GitOps):"
echo "1) Push repo to GitHub"
echo "2) Create secret:  KUBECONFIG_CONTENT  (base64 or literal kubeconfig)"
echo "3) Edit image owner in k8s deploy files: ghcr.io/OWNER → your GitHub org/user"
echo "4) Push to main → CI builds & deploys to your cluster"
echo "————————————————————————————————————————————————————————————"
echo "🛠 If macOS says 'permission denied':  chmod +x *.sh tools/*.py"

