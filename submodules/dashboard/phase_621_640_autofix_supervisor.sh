#!/usr/bin/env bash
# phase_621_640_autofix_supervisor.sh  — NeoLight v4.1 Self-Healing
set -e
echo "🩺 NeoLight :: Phase 621–640 (Autofix Supervisor v4.1)"

mkdir -p logs
touch logs/supervisor.log

# kill any leftovers
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true

# function to (re)start backend
start_backend() {
  echo "🚀 Starting FastAPI backend..." | tee -a logs/supervisor.log
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
}

# function to (re)start daemon
start_daemon() {
  echo "🤖 Starting strategy daemon..." | tee -a logs/supervisor.log
  nohup python3 tools/strategy_daemon.py >> logs/daemon.log 2>&1 &
}

# health check loop
echo "🔁 Supervisor loop engaged (checks every 15 s)" | tee -a logs/supervisor.log
start_backend
sleep 2
start_daemon

while true; do
  # check FastAPI
  STATUS=$(curl -s http://127.0.0.1:8000/api/health | grep -o '"status":"ok"' || true)
  if [ -z "$STATUS" ]; then
    echo "⚠️  Backend down – restarting" | tee -a logs/supervisor.log
    pkill -f "uvicorn backend.main:app" || true
    start_backend
  fi

  # check daemon
  if ! pgrep -f "tools/strategy_daemon.py" >/dev/null; then
    echo "⚠️  Daemon down – restarting" | tee -a logs/supervisor.log
    start_daemon
  fi

  sleep 15
done

