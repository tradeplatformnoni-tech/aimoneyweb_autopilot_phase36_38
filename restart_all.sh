#!/usr/bin/env bash
set -e
echo "♻️  Restarting NeoLight backend + daemon + agent"
pkill -f "uvicorn backend.main:app" || true
pkill -f "tools/strategy_daemon.py" || true
pkill -f "tools/agent_loop.py" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/strategy_daemon.py  >> logs/daemon.log  2>&1 &
nohup python tools/agent_loop.py       >> logs/agent.log   2>&1 &
sleep 2
echo "✅ Done. Health:"; curl -s http://127.0.0.1:8000/api/health || true; echo
