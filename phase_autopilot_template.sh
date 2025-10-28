#!/bin/bash
# -------------------------------
# AI Money Web :: Autopilot Setup
# -------------------------------
set -e

echo "🚀 Starting safe setup..."

# --- prerequisites ---
mkdir -p backend static ai/strategies logs runtime results

# --- create minimal backend/main.py if missing ---
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

# --- create static/dashboard.html if missing ---
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

# --- make sure virtual env is active ---
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "⚠️  No venv found. Create one with: python3 -m venv venv"
  exit 1
fi

# --- restart server ---
pkill -f uvicorn || true
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 2
echo "✅ Server started at http://127.0.0.1:8000/docs"

