#!/bin/zsh
set -e
echo "🧩 QuickFix :: kill & relaunch local server"
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
nohup venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3
open http://127.0.0.1:8000/dashboard || true
echo "✅ Done. Logs → logs/backend.log"
