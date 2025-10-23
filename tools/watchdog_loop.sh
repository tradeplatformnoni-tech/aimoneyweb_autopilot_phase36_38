#!/bin/bash

echo "🔁 Starting NeoLight Watchdog..."

while true; do
  STATUS=$(curl -s http://127.0.0.1:8000/api/health | grep ok)
  if [ -z "$STATUS" ]; then
    echo "❗ FastAPI DOWN — healing with neolight-fix..."
    ./neolight-fix

    echo "📟 Triggering alert..."
    python3 tools/alert_notify.py "FastAPI was down and has been auto-healed."
  else
    echo "✅ FastAPI healthy."
  fi
  sleep 60
done
