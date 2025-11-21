#!/usr/bin/env bash
set -euo pipefail
OUT="$HOME/neolight/logs/system_diagnostic_$(date +%Y%m%d_%H%M%S).txt"

{
echo "=== GUARDIAN SUMMARY ==="
tail -n 60 logs/guardian_stdout.log | grep -E "Starting|failed|healthy|complete" || true
echo
echo "=== ORCHESTRATOR LOG ==="
tail -n 60 logs/intelligence_orchestrator.log || true
echo
echo "=== SMART TRADER LOG ==="
tail -n 60 logs/smart_trader.log || true
echo
echo "=== WEIGHTS BRIDGE LOG ==="
tail -n 60 logs/weights_bridge.log || true
echo
echo "=== DIRECTORY STRUCTURE ==="
find ~/neolight -maxdepth 3 -type d
echo
echo "=== PYTHON ENVIRONMENT ==="
~/neolight/venv/bin/python3 -V
~/neolight/venv/bin/pip list | grep -E "fastapi|uvicorn|pandas|plotly|gTTS|yfinance" || true
echo
echo "=== ACTIVE PROCESSES ==="
ps aux | grep neolight | grep -v grep
} > "$OUT"

echo "✅ Diagnostic file saved: $OUT"
