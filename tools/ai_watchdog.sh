#!/bin/bash
if ! pgrep -f strategy_daemon.py > /dev/null; then
  echo "⚠️ strategy_daemon not running, rebooting..."
  nohup python3 tools/strategy_daemon.py > logs/daemon.log 2>&1 &
  python3 tools/alert_notify.py "⚠️ strategy_daemon auto-restarted!"
fi

