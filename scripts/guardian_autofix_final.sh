#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/neolight"
TARGET="$ROOT/neo_light_fix.sh"
LOG="$ROOT/logs/guardian_autofix_final_$(date +%H%M%S).log"
mkdir -p "$ROOT/logs" "$ROOT/scripts" "$ROOT/agents" "$ROOT/trader" "$ROOT/dashboard"

echo "[⚙️] NeoLight Final Guardian AutoFix started..." | tee "$LOG"

# Ensure scheduler exists
if [[ ! -f "$ROOT/scripts/schedule_all.sh" ]]; then
  echo "[⚠️] Missing schedule_all.sh — recreating..." | tee -a "$LOG"
  cat > "$ROOT/scripts/schedule_all.sh" <<'SCHED'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${HOME}/neolight"
PY="${ROOT}/venv/bin/python3"
LOG="${ROOT}/logs/schedule_stdout.log"
mkdir -p "${ROOT}/logs"
while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔁 Intelligence tick…" >> "$LOG" 2>&1
  nohup "$PY" "$ROOT/agents/intelligence_orchestrator.py" >> "${ROOT}/logs/intel_orchestrator.log" 2>&1 || true
  if [[ -f "${ROOT}/agents/knowledge_integrator.py" ]]; then
    nohup "$PY" "$ROOT/agents/knowledge_integrator.py" >> "${ROOT}/logs/knowledge_integrator.log" 2>&1 || true
  fi
  sleep 14400
done
SCHED
  chmod +x "$ROOT/scripts/schedule_all.sh"
fi

# Replace Guardian script with hardened version
cat > "$TARGET" <<'PATCH'
#!/usr/bin/env bash
set -uo pipefail

ROOT="${HOME}/neolight"
VENV_PY="${ROOT}/venv/bin/python3"
AGENTS_DIR="${ROOT}/agents"
TRADER_DIR="${ROOT}/trader"
DASH_DIR="${ROOT}/dashboard"
SCRIPTS_DIR="${ROOT}/scripts"
GUARDIAN_LOG="${ROOT}/logs/guardian_stdout.log"

mkdir -p "${ROOT}/logs"

log() { printf '%s %s\n' "[$(date '+%F %T')]" "$*" | tee -a "$GUARDIAN_LOG" ; }

if [[ ! -x "$VENV_PY" ]]; then
  log "❌ venv python missing — recreating..."
  python3 -m venv "${ROOT}/venv" || { log "❌ could not create venv"; exit 1; }
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}"

ensure_running() {
  local name="${1:-unknown}"
  local cmd="${2:-}"
  local logfile="${ROOT}/logs/${name}.log"

  if [[ -z "$cmd" ]]; then
    log "⚠️  Missing command for $name — skipping."
    return 1
  fi

  if pgrep -f "$cmd" >/dev/null 2>&1; then
    log "✅ $name already running"
    return 0
  fi

  log "▶️  Starting $name…"
  log "🧩 CMD: $cmd"
  nohup $cmd >> "$logfile" 2>&1 &
  sleep 2

  if pgrep -f "$cmd" >/dev/null 2>&1; then
    log "🟢 $name up"
  else
    log "🔴 $name failed to start — see $logfile"
  fi
}

cd "$ROOT" || exit 1

ensure_running "intelligence_orchestrator" "$VENV_PY $AGENTS_DIR/intelligence_orchestrator.py"
ensure_running "smart_trader" "$VENV_PY $TRADER_DIR/smart_trader.py"
ensure_running "dashboard_v2" "$VENV_PY $DASH_DIR/dashboard_v2_live.py"
ensure_running "scheduler" "bash $SCRIPTS_DIR/schedule_all.sh"
ensure_running "weights_bridge" "$VENV_PY $AGENTS_DIR/weights_bridge.py"

log "⚡ Guardian cycle complete."
PATCH

chmod +x "$TARGET"
chmod +x "$ROOT/scripts/schedule_all.sh"

echo "[🧠] Guardian script patched successfully." | tee -a "$LOG"

# Kill any stuck processes
pkill -f neo_light_fix.sh || true
pkill -f intelligence_orchestrator.py || true
pkill -f smart_trader.py || true
pkill -f weights_bridge.py || true
pkill -f dashboard_v2_live.py || true
sleep 2

# Relaunch Guardian
echo "[🚀] Restarting Guardian..." | tee -a "$LOG"
nohup bash "$TARGET" >> "$ROOT/logs/guardian_stdout.log" 2>&1 & disown
sleep 5
echo "[✅] Guardian restarted — last 40 log lines:" | tee -a "$LOG"
tail -n 40 "$ROOT/logs/guardian_stdout.log" | tee -a "$LOG"
echo "[🏁] NeoLight Final AutoFix complete." | tee -a "$LOG"
