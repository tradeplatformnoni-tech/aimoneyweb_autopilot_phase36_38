#!/bin/bash
set -e

echo "🚀 Fixing FastAPI Backend Startup..."

# Kill anything using port 8000
sudo lsof -ti :8000 | xargs sudo kill -9 2>/dev/null || true
sleep 2

# Check syntax
echo "🧠 Checking Python syntax..."
python -m py_compile backend/main.py || { echo "❌ Syntax error in backend/main.py"; exit 1; }

# Restart backend safely
echo "🔁 Restarting backend..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

# Verify health
echo "💡 Checking health..."
curl -s http://127.0.0.1:8000/ || echo "⚠️  Still not reachable. Run: tail -n 30 logs/backend.log"

