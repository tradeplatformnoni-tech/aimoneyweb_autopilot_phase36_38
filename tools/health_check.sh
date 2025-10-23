#!/usr/bin/env bash
if ! curl -s http://127.0.0.1:8000/api/health >/dev/null; then
  echo "🛠 Restarting FastAPI..."
  pkill -f "uvicorn backend.main:app" || true
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
else
  echo "✅ FastAPI healthy"
fi
