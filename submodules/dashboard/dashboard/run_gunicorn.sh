#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-}"
if [[ -z "$PORT" ]]; then PORT=5050; fi
echo "🚀 Starting dashboard via Gunicorn on :$PORT"
exec gunicorn -w 4 -b "0.0.0.0:${PORT}" "dashboard.flask_app:app"
