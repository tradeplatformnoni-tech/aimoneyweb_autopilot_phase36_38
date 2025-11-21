#!/usr/bin/env bash
set -Eeuo pipefail

PHASE_LABEL="phase_91_150_master"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs";         mkdir -p "$LOG_DIR"
RUNTIME_DIR="${ROOT_DIR}/runtime";  mkdir -p "$RUNTIME_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/${PHASE_LABEL}_${STAMP}.log"
LOCKFILE="${RUNTIME_DIR}/.${PHASE_LABEL}.lock"
HEALTH_URL="http://127.0.0.1:5050/healthz"

# Optional notifications (leave unset to disable)
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT:-}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG_FILE"; }
ok(){ log "$(green "$*")"; }
warn(){ log "$(yellow "$*")"; }
err(){ log "$(red "$*")"; }

notify(){
  local msg="$1"
  [[ -n "$TELEGRAM_TOKEN" && -n "$TELEGRAM_CHAT" ]] && \
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_CHAT}" -d text="${msg}" >/dev/null 2>&1 || true
  [[ -n "$DISCORD_WEBHOOK" ]] && \
    curl -s -H "Content-Type: application/json" -X POST \
      -d "{\"content\": \"${msg}\"}" "${DISCORD_WEBHOOK}" >/dev/null 2>&1 || true
}

need(){ command -v "$1" >/dev/null 2>&1 || { warn "Missing optional: $1"; return 1; }; }

# Single-instance lock
exec 9>"$LOCKFILE" || true
if ! flock -n 9; then
  err "Another ${PHASE_LABEL} instance is running. Exiting."
  exit 0
fi

ok "🚀 Phase 91–150 Master starting"
notify "🧠 Phase 91–150 Master booted on $(hostname)"

# Dependencies (soft)
need jq; need bc; need python3; need flock; need curl

# Ensure sub-scripts exist (created below)
declare -a SHOULD_EXIST=(
  "phases/phase_91_100_neural_tuner.py"
  "phases/phase_101_120_risk_governor.sh"
  "phases/phase_121_130_drawdown_guard.sh"
  "phases/phase_131_140_allocator.py"
  "phases/phase_141_150_telemetry.sh"
)
for f in "${SHOULD_EXIST[@]}"; do
  [[ -f "${ROOT_DIR}/${f}" ]] || { err "Missing: ${f}"; exit 2; }
done

# Wait for dashboard health
for i in {1..10}; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || echo 000)"
  [[ "$code" == "200" ]] && { ok "🟢 Dashboard healthy"; break; }
  warn "Dashboard not healthy ($code) — retrying..."
  sleep 6
done

# Start/monitor sub-phases with self-heal loop
start_sub(){
  local name="$1"; shift
  local cmd=("$@")
  log "▶️  Launching $name: ${cmd[*]}"
  nohup "${cmd[@]}" >> "${LOG_DIR}/${name}.log" 2>&1 &
  echo $!
}

PID_TUNER=$(start_sub "neural_tuner" python3 "${ROOT_DIR}/phases/phase_91_100_neural_tuner.py")
PID_RISK=$(start_sub "risk_governor" bash "${ROOT_DIR}/phases/phase_101_120_risk_governor.sh")
PID_DDG=$(start_sub "drawdown_guard" bash "${ROOT_DIR}/phases/phase_121_130_drawdown_guard.sh")
PID_ALLOC=$(start_sub "allocator" python3 "${ROOT_DIR}/phases/phase_131_140_allocator.py")
PID_TELEM=$(start_sub "telemetry" bash "${ROOT_DIR}/phases/phase_141_150_telemetry.sh")

ok "🧩 Sub-phases launched: tuner=$PID_TUNER risk=$PID_RISK ddg=$PID_DDG alloc=$PID_ALLOC telem=$PID_TELEM"

# Watchdog: restart on failure, soft backoff
BACKOFF=5
while true; do
  sleep 10

  for P in TUNER RISK DDG ALLOC TELEM; do
    VAR="PID_${P}"
    PID="${!VAR:-0}"
    if [[ -n "$PID" ]] && ! kill -0 "$PID" 2>/dev/null; then
      warn "$P died (pid=$PID) — restarting"
      notify "⚠️ ${P} crashed — auto-restarting"
      case "$P" in
        TUNER) PID_TUNER=$(start_sub "neural_tuner" python3 "${ROOT_DIR}/phases/phase_91_100_neural_tuner.py");;
        RISK)  PID_RISK=$(start_sub "risk_governor" bash "${ROOT_DIR}/phases/phase_101_120_risk_governor.sh");;
        DDG)   PID_DDG=$(start_sub "drawdown_guard" bash "${ROOT_DIR}/phases/phase_121_130_drawdown_guard.sh");;
        ALLOC) PID_ALLOC=$(start_sub "allocator" python3 "${ROOT_DIR}/phases/phase_131_140_allocator.py");;
        TELEM) PID_TELEM=$(start_sub "telemetry" bash "${ROOT_DIR}/phases/phase_141_150_telemetry.sh");;
      esac
      sleep "$BACKOFF"; BACKOFF=$(( BACKOFF<60 ? BACKOFF+5 : 60 ))
    fi
  done

  # Health soft gate
  code="$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || echo 000)"
  [[ "$code" != "200" ]] && warn "Dashboard unhealthy ($code) — subs keep running but tuning will be cautious"

done

