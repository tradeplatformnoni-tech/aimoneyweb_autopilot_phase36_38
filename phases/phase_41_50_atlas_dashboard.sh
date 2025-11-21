#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s lastpipe

# ╔══════════════════════════════════════════════════════════════════════════╗
# 🧠  NeoLight Phase 41–50 — Atlas + Dashboard Integration (World-Class)
# ║  Atlas Cognitive Bridge ▸ Guardian ▸ Trader ▸ FastAPI Dashboard          ║
# ║  Self-healing | Auto-rebuild | Version-aware | Multi-agent mesh ready   ║
# ╚══════════════════════════════════════════════════════════════════════════╝
# Usage: ./phases/phase_41_50_atlas_dashboard.sh
# or     ./neo_light_fix.sh (wrapper)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
STAMP="$(date +%Y%m%d_%H%M%S)"
PHASE_LABEL="phase_41_50_atlas_dashboard"
mkdir -p "$LOG_DIR" snapshots

# ---------- Helpers ----------
log() { echo -e "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_DIR/${PHASE_LABEL}_${STAMP}.log"; }
die() { log "❌ $*"; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"; }
port_free() { lsof -ti :"$1" | xargs -r kill -9 || true; }

launch_bg() {
  local name="$1"; shift
  log "▶️  Launching $name: $*"
  (stdbuf -oL -eL bash -lc "$*" | sed -u "s/^/[$name] /") | tee -a "$LOG_DIR/${name}_${STAMP}.log" &
  echo $!
}

health_http() { curl -sS -m 2 -o /dev/null -w '%{http_code}' "$1" || echo 000; }
retry() {
  local tries="$1"; local delay="$2"; shift 2
  local cmd="$*"
  local n=0
  until eval "$cmd"; do
    ((n++)) || true
    [[ "$n" -ge "$tries" ]] && return 1
    sleep "$delay"
  done
}

# ---------- System Checks ----------
need python3; need uvicorn; need curl; need lsof; need jq || true
source "${ROOT_DIR}/.venv/bin/activate" 2>/dev/null || log "ℹ️ venv not found; using system Python"

log "🩺 Pre-flight: verifying ports and environment"
for p in 5050 8080 8090 8091 8092; do port_free "$p"; done

# ---------- Auto-detect structure ----------
ATLAS_PATH=$(find "$ROOT_DIR" -type f -name "atlas_socket.py" | head -n1 || true)
GUARD_PATH=$(find "$ROOT_DIR" -type f -name "guardian_agent.py" | head -n1 || true)
TRADER_PATH=$(find "$ROOT_DIR" -type f -name "trader_agent.py" | head -n1 || true)
DASH_PATH=$(find "$ROOT_DIR" -type f -name "app.py" | grep dashboard | head -n1 || true)

[[ -z "$ATLAS_PATH" ]] && die "atlas_socket.py not found"
[[ -z "$GUARD_PATH" ]] && die "guardian_agent.py not found"
[[ -z "$TRADER_PATH" ]] && die "trader_agent.py not found"
[[ -z "$DASH_PATH" ]] && die "dashboard app.py not found"

# ---------- Launch Services ----------
ATLAS_PID=$(launch_bg atlas "python3 '$ATLAS_PATH'")
GUARD_PID=$(launch_bg guardian "python3 '$GUARD_PATH'")
TRADER_PID=$(launch_bg trader "python3 '$TRADER_PATH' --paper --unified")
DASH_PID=$(launch_bg dashboard "uvicorn ${DASH_PATH%/*.py}.app:app --host 0.0.0.0 --port 5050")

# ---------- Health Monitoring ----------
log "🧬 Initial health probe..."
if ! retry 15 1 "[[ \$(health_http http://127.0.0.1:5050/healthz) == 200 ]]"; then
  log "🔴 Dashboard unhealthy — attempting rebuild"
  port_free 5050
  pip install -r "$ROOT_DIR/dashboard/requirements.txt" --quiet || log "⚠️  No dashboard requirements file found"
  DASH_PID=$(launch_bg dashboard_rebuild "uvicorn ${DASH_PATH%/*.py}.app:app --host 0.0.0.0 --port 5050")
  retry 15 2 "[[ \$(health_http http://127.0.0.1:5050/healthz) == 200 ]]" || die "Dashboard failed after rebuild"
fi

# ---------- Runtime Watchdog ----------
log "👁️  Entering self-healing watchdog loop"
while true; do
  sleep 5
  for entry in "atlas:$ATLAS_PID" "guardian:$GUARD_PID" "trader:$TRADER_PID" "dashboard:$DASH_PID"; do
    svc="${entry%%:*}"; pid="${entry##*:}"
    if ! kill -0 "$pid" 2>/dev/null; then
      log "⚠️  $svc crashed — restarting"
      case "$svc" in
        atlas)     ATLAS_PID=$(launch_bg atlas "python3 '$ATLAS_PATH'");;
        guardian)  GUARD_PID=$(launch_bg guardian "python3 '$GUARD_PATH'");;
        trader)    TRADER_PID=$(launch_bg trader "python3 '$TRADER_PATH' --paper --unified");;
        dashboard) port_free 5050; DASH_PID=$(launch_bg dashboard "uvicorn ${DASH_PATH%/*.py}.app:app --host 0.0.0.0 --port 5050");;
      esac
    fi
  done

  # Web health check
  http=$(health_http http://127.0.0.1:5050/healthz)
  [[ "$http" != 200 ]] && log "🔴 Dashboard returned $http — rebuilding" && port_free 5050 && \
    DASH_PID=$(launch_bg dashboard "uvicorn ${DASH_PATH%/*.py}.app:app --host 0.0.0.0 --port 5050")

  # Risk sanity
  if [[ -f "$ROOT_DIR/trader/state.json" ]]; then
    bal=$(jq -r '.balances.USD // 0' "$ROOT_DIR/trader/state.json" 2>/dev/null || echo 0)
    req=$(jq -r '.pending_order.required_usd // 0' "$ROOT_DIR/trader/state.json" 2>/dev/null || echo 0)
    if (( $(echo "$req > $bal" | bc -l) )); then
      log "⚠️  RiskGuard: order $req > balance $bal — throttling"
      echo '{"throttle":true}' > "$ROOT_DIR/trader/throttle.json"
    fi
  fi

  # Snapshot every 5 min
  now=$(date +%s)
  (( now % 300 < 6 )) && {
    ts=$(date +%Y%m%d_%H%M%S)
    snap="snapshots/$ts"
    mkdir -p "$snap"
    cp -r logs "$ROOT_DIR/trader"/*.json "$ROOT_DIR/ai" "$ROOT_DIR/backend" "$ROOT_DIR/dashboard" 2>/dev/null || true
    log "💾 Snapshot saved at $snap"
  }
done

