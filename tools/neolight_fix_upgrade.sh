#!/usr/bin/env bash
echo "🧠 NeoLight Enhanced AutoFix…"
chmod +x *.sh backend/*.py tools/*.py ai/**/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy psutil || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
sleep 2
echo "✅ AutoFix OK — Visit http://localhost:8000/dashboard"
