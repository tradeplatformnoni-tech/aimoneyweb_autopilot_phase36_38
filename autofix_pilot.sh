#!/usr/bin/env bash
# =============================================
# 🔧 NeoLight :: AutoFix Pilot (Universal Repair)
# =============================================
set -e

echo "🧠 Running NeoLight AutoFix Pilot..."
echo "-----------------------------------"

# --- 1️⃣ Fix Permission Denied for any .sh file ---
echo "🔒 Fixing permission issues for .sh scripts..."
find . -type f -name "*.sh" -exec chmod +x {} \;

# --- 2️⃣ Verify virtual environment ---
if [ -z "$VIRTUAL_ENV" ]; then
  echo "⚠️  No venv active. Activating ./venv if it exists..."
  if [ -d "./venv" ]; then
    source ./venv/bin/activate
  else
    echo "⚙️  Creating new venv..."
    python3 -m venv venv
    source ./venv/bin/activate
    pip install --upgrade pip
  fi
fi

# --- 3️⃣ Ensure dependencies are installed ---
echo "📦 Installing required Python packages (FastAPI, Uvicorn, Requests)..."
pip install --quiet fastapi uvicorn requests python-multipart

# --- 4️⃣ Verify key folders ---
mkdir -p backend static templates runtime logs

# --- 5️⃣ Check if FastAPI is running ---
echo "🔍 Checking backend process..."
if ! pgrep -f "uvicorn backend.main:app" >/dev/null; then
  echo "🚀 Restarting FastAPI backend..."
  pkill -f "uvicorn backend.main:app" || true
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
  sleep 2
else
  echo "✅ FastAPI is already running."
fi

# --- 6️⃣ Check if strategy daemon is running ---
if ! pgrep -f "tools/strategy_daemon.py" >/dev/null; then
  echo "🤖 Restarting strategy daemon..."
  nohup python3 tools/strategy_daemon.py >> logs/daemon.log 2>&1 &
else
  echo "✅ Strategy daemon running."
fi

# --- 7️⃣ Health Check ---
echo "🩺 Checking system health..."
sleep 2
curl -s http://127.0.0.1:8000/api/health || echo "⚠️ Health endpoint not responding yet."

# --- 8️⃣ Summary ---
echo "-----------------------------------"
echo "✅ AutoFix Complete!"
echo "📊 Dashboard: http://localhost:8000/dashboard"
echo "💾 Logs: tail -f logs/backend.log"
echo "-----------------------------------"

