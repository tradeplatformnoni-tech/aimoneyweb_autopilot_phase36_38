#!/bin/bash
if ! curl -s http://127.0.0.1:8000/api/health > /dev/null; then
  echo "❌ Backend down. Triggering cloud fallback."
  # (Insert your remote start commands here)
  python3 tools/alert_notify.py "☁️ Cloud failover triggered"
fi
