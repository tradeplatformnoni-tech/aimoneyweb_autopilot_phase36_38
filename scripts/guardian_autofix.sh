#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/neolight"
TARGET="$ROOT/neo_light_fix.sh"
LOG="$ROOT/logs/guardian_autofix_$(date +%H%M%S).log"
mkdir -p "$ROOT/logs"

echo "[⚙️] NeoLight Guardian AutoFix starting..." | tee "$LOG"

# --- 1️⃣  Fix ensure_running function ---
if grep -q "ensure_running()" "$TARGET" 2>/dev/null; then
  echo "[🧠] Patching ensure_running safety..." | tee -a "$LOG"
  # Replace the first lines of the function to make variables safe
  sed -i '' \
    -e 's/local name=.*/local name="${1:-unknown}"/' \
    -e 's/local cmd=.*/local cmd="${2:-}"/' \
    "$TARGET" 2>/dev/null || true
fi

# --- 2️⃣  Fix scheduler line quoting ---
if grep -q '"/bin/bash"' "$TARGET" 2>/dev/null; then
  echo "[🧩] Fixing scheduler command quoting..." | tee -a "$LOG"
  sed -i '' 's|\"/bin/bash\".*schedule_all.sh\"|/bin/bash $SCRIPTS_DIR/schedule_all.sh|g' "$TARGET" 2>/dev/null || true
fi

# --- 3️⃣  Replace full script with stable version if it's too broken ---
if ! grep -q 'Guardian cycle complete' "$TARGET" 2>/dev/null; then
  echo "[♻️] Replacing Guardian script with clean stable version..." | tee -a "$LOG"
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
  log "❌ venv python missing at $VENV_PY — creating venv..."
  python3 -m venv "${ROOT}/venv" || { log "❌ could not create venv"; exit 1; }
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}"

ensure_running() {
  local name="${1:-unknown}"
  local cmd="${2:-}"
  local logfile="${ROOT}/logs/${name}.log"

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

ensure_running "intelligence_orchestrator" "$VENV_PY $AGENTS_DIR/intelligence_orchestrator.py"
ensure_running "smart_trader" "$VENV_PY $TRADER_DIR/smart_trader.py"
ensure_running "dashboard_v2" "$VENV_PY $DASH_DIR/dashboard_v2_live.py"
ensure_running "scheduler" "/bin/bash $SCRIPTS_DIR/schedule_all.sh"
ensure_running "weights_bridge" "$VENV_PY $AGENTS_DIR/weights_bridge.py"

log "⚡ Guardian cycle complete."
PATCH
fi

chmod +x "$TARGET"

# --- 4️⃣  Restart Guardian ---
echo "[🔄] Restarting Guardian..." | tee -a "$LOG"
pkill -f neo_light_fix.sh || true
pkill -f intelligence_orchestrator.py || true
pkill -f smart_trader.py || true
pkill -f weights_bridge.py || true
pkill -f dashboard_v2_live.py || true
sleep 2

nohup bash "$TARGET" >> "$ROOT/logs/guardian_stdout.log" 2>&1 & disown
sleep 5
echo "[✅] Guardian restarted. Showing latest log:" | tee -a "$LOG"
tail -n 40 "$ROOT/logs/guardian_stdout.log" | tee -a "$LOG"
echo "[🏁] AutoFix complete."
