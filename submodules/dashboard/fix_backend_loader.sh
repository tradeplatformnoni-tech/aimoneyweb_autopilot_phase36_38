#!/bin/bash
echo "🔧 AI Money Web :: Loader Fix Autopilot"

# 1️⃣ Kill anything still on port 8000
echo "🧹 Cleaning old Uvicorn instances..."
for pid in $(sudo lsof -ti :8000); do
  echo "⚔️ Killing PID $pid"
  sudo kill -9 $pid 2>/dev/null || true
done

# 2️⃣ Verify backend.main.py exists
if [ ! -f backend/main.py ]; then
  echo "❌ backend/main.py missing! Recreate it before running this script."
  exit 1
fi

# 3️⃣ Delete rogue root main.py (wrong FastAPI instance)
if [ -f main.py ]; then
  echo "🧼 Removing wrong main.py..."
  rm -f main.py
fi

# 4️⃣ Touch init files to guarantee proper package imports
mkdir -p backend ai ai/strategies
touch backend/__init__.py ai/__init__.py ai/strategies/__init__.py

# 5️⃣ Restart correct backend
echo "🚀 Starting correct backend.main:app..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

# 6️⃣ Verify correct app started
if curl -s http://127.0.0.1:8000/docs | grep -q "AI Money Web"; then
  echo "✅ Correct backend running at http://127.0.0.1:8000"
else
  echo "⚠️ Still seeing default FastAPI. Check backend.main:app path or imports."
fi

