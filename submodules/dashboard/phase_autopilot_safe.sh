#!/bin/bash
# -----------------------------------------------
# AI Money Web :: Safe Autopilot Quick-Fix Setup
# -----------------------------------------------
set -e

echo "🚀 Starting safe setup..."

# --- 0.  Clean up any old Uvicorn instances ---
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing old process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# --- 1.  Create project folders ---
mkdir -p backend static logs ai/strategies runtime results

# --- 2.  Create backend/main.py ---
cat > backend/main.py <<'PYCODE'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="AI Money Web Autopilot Demo")

@app.get("/")
def root():
    return {"message": "server ok"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html = "<h1>Dashboard</h1><p>Autopilot demo running.</p>"
    return HTMLResponse(content=html, status_code=200)
PYCODE

# --- 3.  Create static/dashboard.html ---
cat > static/dashboard.html <<'HTML'
<!DOCTYPE html>
<html>
<head><title>Autopilot Dashboard</title></head>
<body>
<h1>AI Money Web Autopilot</h1>
<p>Dashboard ready.</p>
</body>
</html>
HTML

# --- 4.  Ensure virtual environment active ---
if [ ! -d "venv" ]; then
  echo "⚠️  No virtual environment found. Create one first with: python3 -m venv venv"
  exit 1
fi
source venv/bin/activate

# --- 5.  Start backend cleanly ---
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "✅ Backend running on http://127.0.0.1:8000"
echo "💡 Dashboard:  http://127.0.0.1:8000/dashboard"

