#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/neolight"
TARGET="$ROOT/neo_light_fix.sh"
LOG="$ROOT/logs/guardian_autofix_permanent_$(date +%H%M%S).log"
mkdir -p "$ROOT/logs" "$ROOT/scripts" "$ROOT/agents" "$ROOT/trader" "$ROOT/dashboard"

echo "[⚙️] NeoLight Permanent Guardian AutoFix starting..." | tee "$LOG"

# --- Guardian Script Rewrite ---
cat > "$TARGET" <<'PATCH'
#!/usr/bin/env bash
set +u   # temporarily disable strict var checks for stability

ROOT="${HOME}/neolight"
VENV_PY="${ROOT}/venv/bin/python3"
AGENTS_DIR="${ROOT}/agents"
TRADER_DIR="${ROOT}/trader"
DASH_DIR="${ROOT}/dashboard"
SCRIPTS_DIR="${ROOT}/scripts"
GUARDIAN_LOG="${ROOT}/logs/guardian_stdout.log"

mkdir -p "${ROOT}/logs"

log() {
  local msg="${*:-<no message>}"
  printf '%s %s\n' "[$(date '+%F %T')]" "$msg" | tee -a "$GUARDIAN_LOG" 2>/dev/null || echo "[$(date '+%F %T')] $msg"
}

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
    return
  fi

  cd "$ROOT" || exit 1

  if pgrep -f "$cmd" >/dev/null 2>&1; then
    log "✅ $name already running"
    return
  fi

  log "▶️  Starting $name..."
  log "🧩 CMD: $cmd"
  nohup bash -lc "$cmd" >> "$logfile" 2>&1 &
  sleep 2

  if pgrep -f "$cmd" >/dev/null 2>&1; then
    log "🟢 $name up"
  else
    log "🔴 $name failed to start — see $logfile"
  fi
}

# Ensure we're in correct directory before launching anything
cd "$ROOT" || exit 1

ensure_running "intelligence_orchestrator" "$VENV_PY $AGENTS_DIR/intelligence_orchestrator.py"
ensure_running "smart_trader" "$VENV_PY $TRADER_DIR/smart_trader.py"
ensure_running "dashboard_v2" "$VENV_PY $DASH_DIR/dashboard_v2_live.py"
ensure_running "scheduler" "bash $SCRIPTS_DIR/schedule_all.sh"
ensure_running "weights_bridge" "$VENV_PY $AGENTS_DIR/weights_bridge.py"

log "⚡ Guardian cycle complete."
PATCH

chmod +x "$TARGET"

echo "[🔁] Restarting Guardian with hardened version..." | tee -a "$LOG"
pkill -f neo_light_fix.sh || true
pkill -f intelligence_orchestrator.py || true
pkill -f smart_trader.py || true
pkill -f weights_bridge.py || true
pkill -f dashboard_v2_live.py || true
sleep 2

nohup bash "$TARGET" >> "$ROOT/logs/guardian_stdout.log" 2>&1 & disown
sleep 5
echo "[✅] Guardian restarted. Latest status:" | tee -a "$LOG"
tail -n 40 "$ROOT/logs/guardian_stdout.log" | tee -a "$LOG"
echo "[🏁] Permanent AutoFix complete." | tee -a "$LOG"
