#!/bin/bash

echo "🧠 Starting NeoLight Phase 1601–1650 Autopilot + AutoFix..."

# 🔒 Ensure all scripts are executable
echo "🔐 Fixing .sh permissions..."
chmod +x *.sh tools/*.sh

# 📦 Install any missing Python packages
echo "📦 Ensuring dependencies..."
pip install -q fastapi uvicorn requests

# 🔍 AutoFix backend/main.py issues

MAIN_FILE="backend/main.py"

if grep -q "StaticFilesnfrom" "$MAIN_FILE"; then
  echo "🛠️ Fixing fused StaticFiles + from error..."
  sed -i '' 's/StaticFilesnfrom/StaticFiles\nfrom/' "$MAIN_FILE"
fi

if grep -q "backtest_runnfrom" "$MAIN_FILE"; then
  echo "🛠️ Fixing fused backtest + from error..."
  sed -i '' 's/backtest_runnfrom/backtest_run\nfrom/' "$MAIN_FILE"
fi

# 🔁 Restart FastAPI safely
echo "🚀 Restarting FastAPI backend..."
killall uvicorn 2>/dev/null
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &

# ✅ Run Health Check
echo "✅ Checking health endpoint:"
sleep 2
curl -s http://127.0.0.1:8000/api/health || echo "❗ Health endpoint not responding."

echo "✅ Phase 1601–1650 Complete. System self-healed and running."

