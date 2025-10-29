#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s lastpipe

# 🧠 NeoLight Phase 41–50 — Atlas + Dashboard Integration (World-class)
# Assess → Diagnose → Intervene → Recover (Self-healing)
# Usage: PHASE=41-50 ./neo_light_fix.sh  or  ./phases/phase_41_50_atlas_dashboard.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
PHASE_LABEL="phase_41_50_atlas_dashboard"

# ---------- Helpers ----------
log(){ echo -e "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_DIR/${PHASE_LABEL}_${STAMP}.log"; }

die(){ log "❌ $*"; exit 1; }

need(){ command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"; }

port_free(){ lsof -ti :"$1" | xargs -r kill -9 || true; }

launch_bg(){ 
  local name="$1"; shift
  log "▶️  Launching $name: $*"
  (stdbuf -oL -eL bash -lc "$*" | sed -u "s/^/[$name] /") | tee -a "$LOG_DIR/${name}_${STAMP}.log" &
  echo $!
}

health_http(){ curl -sS -m 2 -o /dev/null -w '%{http_code}' "$1" || echo 000; }

retry(){
  local tries="$1"; shift
  local delay="$1"; shift
  local cmd="$*"
  local n=0
  until eval "$cmd"; do
    ((n++)) || true
    [[ "$n" -ge "$tries" ]] && return 1
    sleep "$delay"
  done
}

# ---------- Preconditions ----------
need python3; need uvicorn; need curl; need lsof; need jq || true
source "${ROOT_DIR}/venv/bin/activate" 2>/dev/null || log "ℹ️ venv not found; relying on system Python"

# Kill conflicting ports
port_free 5050; port_free 8080; port_free 8090; port_free 8091; port_free 8092

# ---------- Start Services ----------
ATLAS_PID="$(launch_bg atlas_socket "python3 atlas/atlas_socket.py")"
GUARD_PID="$(launch_bg guardian "python3 guardian/guardian_agent.py")"
TRADER_PID="$(launch_bg trader "python3 trader/trader_agent.py --paper --unified")"
DASH_PID="$(launch_bg dashboard "uvicorn dashboard.app:app --host 0.0.0.0 --port 5050")"

# ---------- Health Checks ----------
log "🩺 Probing health endpoints..."
if ! retry 10 1 "test "$(health_http http://127.0.0.1:5050/healthz)" = 200"; then
  log "🔴 Dashboard unhealthy on :5050 — attempting rebuild"
  port_free 5050
  DASH_PID="$(launch_bg dashboard_rebuild "python3 -m pip install -r dashboard/requirements.txt && uvicorn dashboard.app:app --host 0.0.0.0 --port 5050")"
  retry 10 1 "test "$(health_http http://127.0.0.1:5050/healthz)" = 200" || die "Dashboard failed after rebuild"
fi

# ---------- Runtime Watchdog ----------
log "👁️  Entering watchdog loop (self-healing)"
while true; do
  sleep 5
  # Check processes
  for name in atlas_socket:$ATLAS_PID guardian:$GUARD_PID trader:$TRADER_PID dashboard:$DASH_PID; do
    p="${name##*:}"; n="${name%%:*}"
    if ! kill -0 "$p" 2>/dev/null; then
      log "⚠️  $n died — restarting"
      case "$n" in
        atlas_socket) ATLAS_PID="$(launch_bg atlas_socket "python3 atlas/atlas_socket.py")";;
        guardian) GUARD_PID="$(launch_bg guardian "python3 guardian/guardian_agent.py")";;
        trader) TRADER_PID="$(launch_bg trader "python3 trader/trader_agent.py --paper --unified")";;
        dashboard) port_free 5050; DASH_PID="$(launch_bg dashboard "uvicorn dashboard.app:app --host 0.0.0.0 --port 5050")";;
      esac
    fi
  done

  # Check HTTP health
  http=$(health_http http://127.0.0.1:5050/healthz)
  [[ "$http" != 200 ]] && log "🔴 Dashboard unhealthy ($http)" && port_free 5050 && DASH_PID="$(launch_bg dashboard "uvicorn dashboard.app:app --host 0.0.0.0 --port 5050")"

  # Lightweight risk sanity: check positions vs balance to avoid 403 insufficient balance
  if [[ -f trader/state.json ]]; then
    bal=$(jq -r '.balances.USD // 0' trader/state.json 2>/dev/null || echo 0)
    req=$(jq -r '.pending_order.required_usd // 0' trader/state.json 2>/dev/null || echo 0)
    if [[ "$req" != 0 && "$bal" != 0 ]]; then
      awk "BEGIN{if($req>$bal) exit 0; else exit 1}" </dev/null && {
        log "⚠️  RiskGuard: requested $req > balance $bal — throttling next order size"
        echo '{"throttle":true}' > trader/throttle.json
      } || true
    fi
  fi

  # Periodic snapshots
  if (( $(date +%s) % 300 < 6 )); then
    ts="$(date +%Y%m%d_%H%M%S)"
    mkdir -p snapshots/$ts
    cp -r logs trader/*.json trader/logs* atlas/logs* dashboard/logs* 2>/dev/null || true
    log "💾 Snapshot @ $ts"
  fi

 done
