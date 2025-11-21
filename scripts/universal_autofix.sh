#!/usr/bin/env bash
set -euo pipefail
echo "🧠 NeoLight — Universal AutoFix Script Starting..."

# --- 1️⃣ Fix SPY string math bug in dashboard_v3_playground.py ---
DASH_FILE="$HOME/neolight/dashboard/dashboard_v3_playground.py"
if grep -q "spy\['spy_norm'\]" "$DASH_FILE"; then
  echo "🔧 Patching SPY normalization logic..."
  sed -i '' '/spy\["spy_norm"\]/i\
    spy["SPY_Close"] = pd.to_numeric(spy["SPY_Close"], errors="coerce")\nspy.dropna(subset=["SPY_Close"], inplace=True)
  ' "$DASH_FILE"
  echo "✅ SPY fix applied."
else
  echo "ℹ️ SPY normalization already fixed or not found."
fi

# --- 2️⃣ Recreate missing scheduler if needed ---
SCHED_FILE="$HOME/neolight/scripts/schedule_all.sh"
if [[ ! -f "$SCHED_FILE" ]]; then
  echo "🧩 Creating missing schedule_all.sh..."
  mkdir -p "$HOME/neolight/scripts"
  cat > "$SCHED_FILE" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${HOME}/neolight"
PY="${ROOT}/venv/bin/python3"
LOG="${ROOT}/logs/schedule_stdout.log"

while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔁 Intelligence tick…" >> "$LOG" 2>&1
  nohup "$PY" "$ROOT/agents/intelligence_orchestrator.py" >> "$ROOT/logs/intel_orchestrator.log" 2>&1 || true
  nohup "$PY" "$ROOT/agents/weights_bridge.py" >> "$ROOT/logs/weights_bridge.log" 2>&1 || true
  sleep 14400
done
SH
  chmod +x "$SCHED_FILE"
  echo "✅ schedule_all.sh recreated."
else
  echo "ℹ️ schedule_all.sh already exists."
fi

# --- 3️⃣ Restart Guardian cleanly ---
echo "🌀 Restarting NeoLight Guardian..."
pkill -f neo_light_fix.sh || true
nohup bash "$HOME/neolight/neo_light_fix.sh" >> "$HOME/neolight/logs/guardian_stdout.log" 2>&1 & disown
sleep 3
tail -n 20 "$HOME/neolight/logs/guardian_stdout.log"

echo "✅ All fixes applied. Guardian restarted."
echo "🌐 To relaunch dashboard:  NEOLIGHT_DASH_PORT=8100 ~/neolight/venv/bin/python3 ~/neolight/dashboard/dashboard_v3_playground.py"
