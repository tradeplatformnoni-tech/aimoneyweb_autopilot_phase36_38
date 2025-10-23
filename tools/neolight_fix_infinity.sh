#!/usr/bin/env bash
echo "🧠 NeoLight AutoFix∞ — Infinite Resilience Mode"
chmod +x *.sh backend/*.py tools/*.py ai/**/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy psutil || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/risk_daemon.py >> logs/risk.log 2>&1 &
nohup python tools/sentiment_daemon.py >> logs/sentiment.log 2>&1 &
nohup python tools/allocator_cron.py >> logs/allocator.log 2>&1 &
nohup python -m ai.memory.experience_logger >> logs/memory.log 2>&1 &
nohup python -m ai.insight.strategy_rebuilder >> logs/rebuilder.log 2>&1 &
nohup python -m ai.memory.cloud_sync >> logs/cloudsync.log 2>&1 &
sleep 3
echo "✅ AutoFix∞ complete — all subsystems revived"
echo "💾 Experience log: runtime/experience_log.jsonl"
echo "🌐 Dashboard: http://localhost:8000/dashboard_v48.html"
