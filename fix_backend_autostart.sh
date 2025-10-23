#!/bin/bash
echo "🧹  Phase-Safe Autostart Fix for AI-Money-Web"

# 1️⃣ Kill any rogue Python or uvicorn on port 8000
echo "🔍  Searching for old processes on port 8000..."
for pid in $(sudo lsof -ti :8000); do
  echo "⚔️  Killing PID $pid (holding :8000)"
  sudo kill -9 $pid 2>/dev/null || true
done

# 2️⃣ Verify port is free
if sudo lsof -i :8000 >/dev/null; then
  echo "⚠️  Port 8000 still busy, waiting 2 s..."
  sleep 2
fi

# 3️⃣ Delete stray root-level main.py if present
if [ -f "main.py" ]; then
  echo "🧼  Removing root main.py to prevent wrong app start..."
  rm -f main.py
fi

# 4️⃣ Activate venv & start correct backend
echo "🚀  Launching backend.main:app..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

# 5️⃣ Confirm server up
if curl -s http://127.0.0.1:8000/docs | grep -q "openapi"; then
  echo "✅  Backend running correctly on http://127.0.0.1:8000"
else
  echo "❌  Backend did not start — check logs/backend.log"
fi

