#!/bin/bash

echo "🌐 Starting Phase 1201–1300: Cloud Console Deployment Center..."

mkdir -p console
mkdir -p api/console

# HTML Console UI
cat <<EOT > console/index.html
<!DOCTYPE html>
<html>
<head>
    <title>NeoLight Cloud Console</title>
    <style>
        body { font-family: monospace; background: #111; color: #0f0; padding: 20px; }
        h1 { color: #fff; }
        button { background: #0f0; color: #111; margin: 5px; padding: 10px; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>NeoLight Deployment Center</h1>
    <div id="output"></div>
    <button onclick="trigger('/api/console/retrain')">📚 Reinforce Brain</button>
    <button onclick="trigger('/api/console/restart')">♻️ Restart System</button>
    <button onclick="trigger('/api/console/atlas/launch')">⚡ Launch Atlas</button>
    <button onclick="trigger('/api/console/health')">🩺 System Health</button>

    <script>
        function trigger(endpoint) {
            fetch(endpoint).then(res => res.json()).then(data => {
                document.getElementById('output').innerText = JSON.stringify(data, null, 2);
            });
        }
    </script>
</body>
</html>
EOT

# FastAPI Endpoints
cat <<EOT > api/console/routes.py
from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/api/console/retrain")
def reinforce():
    return {"message": "🧠 Reinforcement triggered (simulated)"}

@router.get("/api/console/restart")
def restart():
    os.system("pm2 restart neolight")
    return {"message": "♻️ Restart command issued (via PM2)"}

@router.get("/api/console/atlas/launch")
def launch_atlas():
    return {"message": "⚡ Atlas Agent Launch initiated (stub)"}

@router.get("/api/console/health")
def health():
    return {"status": "ok", "uptime": "stable", "mode": "LIVE"}
EOT

# Mount static files & register routes in backend/main.py
main_file="backend/main.py"
if grep -q "console" "$main_file"; then
    echo "✅ Console already integrated."
else
    echo "⚙️ Patching backend/main.py for Cloud Console..."
    sed -i '' '/from fastapi import FastAPI/a\
from fastapi.staticfiles import StaticFiles\nfrom api.console import routes as console_routes' $main_file

    sed -i '' '/app = FastAPI()/a\
app.include_router(console_routes.router)\napp.mount("/dashboard/console", StaticFiles(directory="console", html=True), name="console")' $main_file
fi

# Restart with fallback
pm2 restart neolight || echo "⚠️ PM2 not found. Restart manually."

echo "✅ Cloud Console UI ready!"
echo "🌐 Open it at: http://localhost:8000/dashboard/console"

