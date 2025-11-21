#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/neolight"
OUT="$ROOT/logs/autoreport_$(date +%Y%m%d_%H%M%S).txt"

echo "🧩 NeoLight System Health Autoreport — $(date)" > "$OUT"
echo >> "$OUT"

# Include Guardian summary
echo "=== GUARDIAN STATUS ===" >> "$OUT"
bash "$ROOT/scripts/guardian_status.sh" >> "$OUT" 2>&1 || true
echo >> "$OUT"

# Capture latest orchestrator brain state
echo "=== ORCHESTRATOR BRAIN STATE ===" >> "$OUT"
grep -E "risk_scaler|confidence|Orchestrator updated brain" "$ROOT/logs/intelligence_orchestrator.log" | tail -n 6 >> "$OUT" || true
echo >> "$OUT"

# Capture latest allocations
echo "=== CURRENT ALLOCATIONS ===" >> "$OUT"
grep -E "allocations_override.json|✅ allocations" "$ROOT/logs/weights_bridge.log" | tail -n 3 >> "$OUT" || true
echo >> "$OUT"

# Try to read actual allocation file if exists
if [ -f "$ROOT/runtime/allocations_override.json" ]; then
  echo "=== ALLOCATION FILE CONTENTS ===" >> "$OUT"
  cat "$ROOT/runtime/allocations_override.json" >> "$OUT" 2>&1 || true
  echo >> "$OUT"
fi

# Try to read brain file if exists
if [ -f "$ROOT/runtime/atlas_brain.json" ]; then
  echo "=== ATLAS BRAIN STATE ===" >> "$OUT"
  cat "$ROOT/runtime/atlas_brain.json" >> "$OUT" 2>&1 || true
  echo >> "$OUT"
fi

# Check for auto-patch activity
echo "=== AUTO-PATCH ACTIVITY (code_fix_hook) ===" >> "$OUT"
grep -E "code_fix_hook|invoking code_fix" "$ROOT/logs"/*.log 2>/dev/null | tail -n 5 >> "$OUT" || echo "No auto-patch activity detected" >> "$OUT"
echo >> "$OUT"

# Telegram push (replace with your actual bot + chat ID)
TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

if [ -n "$TOKEN" ] && [ -n "$CHAT_ID" ]; then
  REPORT_TEXT="$(cat "$OUT")"
  curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    --data-urlencode text="$REPORT_TEXT" >/dev/null 2>&1 || true
  echo "✅ Autoreport sent to Telegram and saved: $OUT"
else
  echo "⚠️  Telegram credentials not set (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID). Report saved: $OUT"
fi

