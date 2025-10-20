#!/bin/zsh
echo "🧠 Quick Fix Autopilot :: Starting..."

# 1️⃣ Create backups + logs folders
mkdir -p backups logs tools test static/css

# 2️⃣ Backup main.py
timestamp=$(date +"%Y%m%d_%H%M%S")
if [ -f main.py ]; then
  cp main.py backups/main.py.$timestamp.bak
  echo "✅ Backup created: backups/main.py.$timestamp.bak"
else
  echo "⚠️ No main.py found, continuing..."
fi

# 3️⃣ Run syntax corrector if available
if [ -f tools/auto_syntax_corrector.py ]; then
  echo "🩹 Running syntax corrector..."
  venv/bin/python3 tools/auto_syntax_corrector.py || echo "⚠️ Corrector script failed, continuing..."
else
  echo "⚠️ No syntax corrector found."
fi

# 4️⃣ Ensure dependencies
echo "🐍 Ensuring dependencies..."
venv/bin/pip install --quiet requests fastapi uvicorn

# 5️⃣ Free up port 8000
echo "🔪 Freeing port 8000..."
kill -9 $(lsof -ti:8000) 2>/dev/null && echo "✅ Port cleared." || echo "✅ No process using port 8000."

# 6️⃣ Launch FastAPI backend
echo "🚀 Starting backend..."
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 5

# 7️⃣ Verify API health
echo "🧪 Checking backend health..."
if curl -s http://127.0.0.1:8000/ | grep -q "AI Money Web"; then
  echo "✅ Backend running fine!"
else
  echo "❌ Backend failed to respond. Check logs/backend.log"
  tail -n 20 logs/backend.log
fi

# 8️⃣ Open dashboard
echo "🌐 Opening dashboard..."
open http://127.0.0.1:8000/dashboard

# 9️⃣ Done
echo "✅ Quick Fix Autopilot complete. Logs → ./logs/backend.log"

