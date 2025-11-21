#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/neolight"
LOG="$ROOT/logs/guardian_stdout.log"

echo "=== GUARDIAN STATUS @ $(date '+%F %T') ==="
echo "-- recent guardian decisions --"
tail -n 60 "$LOG" | grep -E "Starting|failed|healthy|complete|auto-?patch|restart" || true

echo; echo "-- processes --"
ps aux | egrep "intelligence_orchestrator.py|smart_trader.py|weights_bridge.py" | egrep -v "egrep" || echo "no agents running"

echo; echo "-- per-agent last 40 lines --"
for f in intelligence_orchestrator smart_trader weights_bridge; do
  echo; echo "[$f.log]"; tail -n 40 "$ROOT/logs/${f}.log" || true
done
