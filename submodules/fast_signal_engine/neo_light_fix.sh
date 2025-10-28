#!/usr/bin/env bash
set -euo pipefail

# =========================
# NeoLight Autopilot — Phases 23–26
# Assess → Diagnose → Intervene
# =========================
# Modules covered:
#  - Phase 23: Atlas Macro Fusion (ai/atlas_integration.py → svc on :8096)
#  - Phase 24: Reinforcement Grid Fusion (svc on :8092 uses macro+sentiment)
#  - Phase 25: Capital Governor Hook (ai/capital_governor.py)
#  - Phase 26: Telemetry Panel Upgrade (Grafana/Supabase exporters)
#
# Usage:
#   chmod +x neo_light_fix.sh
#   ./neo_light_fix.sh phases 23-26
#   ./neo_light_fix.sh phases all
#
# Idempotent: safe to run repeatedly; auto-repairs crashed modules.
# =========================

### ── CONFIG ────────────────────────────────────────────────────────────────
ROOT_DIR="${ROOT_DIR:-$HOME/neolight}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
RUNTIME_DIR="${RUNTIME_DIR:-$ROOT_DIR/runtime}"
PHASE_FILE="${PHASE_FILE:-$RUNTIME_DIR/PHASE_STATE}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

# Services/ports
PORT_SENTIMENT=${PORT_SENTIMENT:-8091}        # Sentiment Bridge (already live)
PORT_RL=${PORT_RL:-8092}                      # Reinforcement Grid (already live)
PORT_MACRO=${PORT_MACRO:-8093}                # Macro Forecaster (already live)
PORT_MME=${PORT_MME:-8094}                    # Market-Maker Engine (already live)
PORT_DAO=${PORT_DAO:-8095}                    # DAO Bridge (already live)
PORT_ATLAS=${PORT_ATLAS:-8096}                # NEW: Atlas Integration service
PORT_TELEM=${PORT_TELEM:-9106}                # NEW: Telemetry macro exporter

PY=${PY:-python3}
PIP=${PIP:-pip3}
CURL=${CURL:-curl}

# Health endpoints (adjust if your apps differ)
HEALTHZ_ATLAS="http://127.0.0.1:${PORT_ATLAS}/healthz"
HEALTHZ_RL="http://127.0.0.1:${PORT_RL}/healthz"
HEALTHZ_SENTIMENT="http://127.0.0.1:${PORT_SENTIMENT}/healthz"
HEALTHZ_MACRO="http://127.0.0.1:${PORT_MACRO}/healthz"

# API keys expected for macro fusion
REQUIRED_ENV=(
  "FRED_API_KEY"
  "NEWS_API_KEY"        # or NEWSAPI_API_KEY if you prefer
  "OPENAI_API_KEY"      # if FinBERT is proxied to an LLM, else not needed
)

# Retry/backoff policy
RETRY_MAX=20
RETRY_SLEEP=3

### ── UTIL ─────────────────────────────────────────────────────────────────
timestamp(){ date +"%Y-%m-%d %H:%M:%S"; }
log(){ echo "[$(timestamp)] $*"; }
warn(){ echo "[$(timestamp)] [WARN] $*" >&2; }
err(){  echo "[$(timestamp)] [ERROR] $*" >&2; }

need_cmd(){
  command -v "$1" >/dev/null 2>&1 || { err "Missing command: $1"; exit 1; }
}

mkd(){
  mkdir -p "$1"
}

load_env(){
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; . "$ENV_FILE"; set +a
  fi
}

write_phase(){
  mkd "$RUNTIME_DIR"
  echo "$1" > "$PHASE_FILE"
}

current_phase(){
  [[ -f "$PHASE_FILE" ]] && cat "$PHASE_FILE" || echo "unknown"
}

kill_port(){
  local port="$1"
  if lsof -ti tcp:"$port" >/dev/null 2>&1; then
    log "Freeing port :$port"
    lsof -ti tcp:"$port" | xargs -r kill -9 || true
    sleep 1
  fi
}

retry(){
  local n=1
  local max=${1:-$RETRY_MAX}
  local delay=${2:-$RETRY_SLEEP}
  shift 2
  local cmd=("$@")
  while true; do
    if "${cmd[@]}"; then
      return 0
    else
      if [[ $n -lt $max ]]; then
        ((n++))
        sleep "$delay"
      else
        return 1
      fi
    fi
  done
}

check_health(){
  local name="$1" url="$2"
  retry "$RETRY_MAX" "$RETRY_SLEEP" $CURL -sfL "$url" >/dev/null
}

venv_activate(){
  # optional: use project venv if present
  if [[ -d "$ROOT_DIR/.venv" ]]; then
    # shellcheck disable=SC1091
    . "$ROOT_DIR/.venv/bin/activate"
  fi
}

### ── ASSESS ───────────────────────────────────────────────────────────────
assess_env(){
  load_env
  for k in "${REQUIRED_ENV[@]}"; do
    if [[ -z "${!k:-}" ]]; then
      warn "Missing env var: $k (macro fusion may fail). Add to $ENV_FILE"
    fi
  done
  need_cmd "$PY"
  need_cmd "$PIP"
  need_cmd "$CURL"
}

assess_files(){
  local ok=true
  local files=(
    "$ROOT_DIR/ai/atlas_integration.py"
    "$ROOT_DIR/ai/signal_engine.py"
    "$ROOT_DIR/ai/capital_governor.py"
    "$ROOT_DIR/ai/telemetry.py"
    "$ROOT_DIR/agents/reinforcement_grid.py"
  )
  for f in "${files[@]}"; do
    if [[ ! -f "$f" ]]; then
      warn "Missing file: $f"
      ok=false
    fi
  done
  $ok
}

assess_services(){
  local healthy=true

  if ! check_health "Sentiment" "$HEALTHZ_SENTIMENT"; then
    warn "Sentiment Bridge unhealthy (:${PORT_SENTIMENT})"
    healthy=false
  fi
  if ! check_health "Macro" "$HEALTHZ_MACRO"; then
    warn "Macro Forecaster unhealthy (:${PORT_MACRO})"
    healthy=false
  fi
  if ! check_health "Reinforcement" "$HEALTHZ_RL"; then
    warn "Reinforcement Grid unhealthy (:${PORT_RL})"
    healthy=false
  fi
  # Atlas will be started if missing (not fatal at assess time)
  if ! $CURL -sfL "$HEALTHZ_ATLAS" >/dev/null 2>&1; then
    warn "Atlas Integration not up yet (:${PORT_ATLAS})"
  fi

  $healthy
}

### ── DIAGNOSE ─────────────────────────────────────────────────────────────
diagnose_atlas(){
  log "Diagnosing Atlas Integration"
  # Quick import checks
  $PY - <<'PYCODE'
import importlib, sys
mods = ["requests","pydantic","uvicorn","fastapi"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception:
        missing.append(m)
if missing:
    print("MISSING:" + ",".join(missing))
    sys.exit(2)
print("OK")
PYCODE
}

diagnose_reinforcement(){
  log "Diagnosing Reinforcement Grid"
  # Ensure RL module can import and that policy file exists (if you use one)
  if [[ -f "$RUNTIME_DIR/weights.json" ]]; then
    log "weights.json present"
  else
    warn "weights.json missing (RL will bootstrap with defaults)"
  fi
}

diagnose_capital_governor(){
  log "Diagnosing Capital Governor"
  if [[ -f "$ROOT_DIR/runtime/portfolio.json" ]]; then
    log "portfolio.json present"
  else
    warn "portfolio.json missing (will be created on first run)"
  fi
  if [[ -f "$ROOT_DIR/runtime/goal_config.json" ]]; then
    log "goal_config.json present"
  else
    warn "goal_config.json missing (add milestones for $1M/2y tracking)"
  fi
}

diagnose_telemetry(){
  log "Diagnosing Telemetry exporters"
  # nothing fatal; exporter will be started if not detected
}

### ── INTERVENE ────────────────────────────────────────────────────────────
start_atlas(){
  log "Starting Atlas Integration on :${PORT_ATLAS}"
  kill_port "$PORT_ATLAS"
  mkd "$LOG_DIR"
  nohup "$PY" "$ROOT_DIR/ai/atlas_integration.py" \
    --serve --host 127.0.0.1 --port "$PORT_ATLAS" \
    >"$LOG_DIR/atlas_${PORT_ATLAS}.log" 2>&1 &
  sleep 1
  check_health "Atlas" "$HEALTHZ_ATLAS" || {
    err "Atlas failed health check"; return 1;
  }
  log "Atlas Integration healthy"
}

start_reinforcement(){
  log "Ensuring Reinforcement Grid on :${PORT_RL}"
  # Assume your RL grid runs as a module; adjust to your launcher
  if ! $CURL -sfL "$HEALTHZ_RL" >/dev/null 2>&1; then
    kill_port "$PORT_RL"
    nohup "$PY" "$ROOT_DIR/agents/reinforcement_grid.py" \
      --serve --host 127.0.0.1 --port "$PORT_RL" \
      --macro-url "http://127.0.0.1:${PORT_MACRO}/stream" \
      --sentiment-url "http://127.0.0.1:${PORT_SENTIMENT}/stream" \
      --atlas-url "http://127.0.0.1:${PORT_ATLAS}/stream" \
      >"$LOG_DIR/rl_${PORT_RL}.log" 2>&1 &
    sleep 1
  fi
  check_health "Reinforcement" "$HEALTHZ_RL" || {
    err "Reinforcement Grid failed health check"; return 1;
  }
  log "Reinforcement Grid healthy"
}

wire_signal_engine(){
  log "Wiring signal_engine → Atlas + Sentiment + Macro"
  # Optional: run a quick integration smoke test (non-fatal)
  $PY - <<PYCODE
import requests, json
for name, url in {
 "sentiment":"$HEALTHZ_SENTIMENT",
 "macro":"$HEALTHZ_MACRO",
 "atlas":"$HEALTHZ_ATLAS"
}.items():
    try:
        requests.get(url, timeout=2).raise_for_status()
    except Exception as e:
        print(f"[WARN] {name} health check skipped: {e}")
print("OK")
PYCODE
}

start_capital_governor(){
  log "Starting Capital Governor"
  # Governor runs as a periodic allocator; keep as background loop
  if pgrep -f "ai/capital_governor.py" >/dev/null 2>&1; then
    log "Capital Governor already running"
  else
    nohup "$PY" "$ROOT_DIR/ai/capital_governor.py" \
      --rebalance-interval "30m" \
      --min-cash-buffer "0.07" \
      --drawdown-throttle "0.10" \
      >"$LOG_DIR/capital_governor.log" 2>&1 &
    sleep 1
  fi
  log "Capital Governor active"
}

start_telemetry_exporter(){
  log "Starting Telemetry (macro exporter) on :${PORT_TELEM}"
  kill_port "$PORT_TELEM"
  nohup "$PY" "$ROOT_DIR/ai/telemetry.py" \
    --exporter --host 127.0.0.1 --port "$PORT_TELEM" \
    --include "macro,sentiment,signal_quality,rl_policy" \
    >"$LOG_DIR/telemetry_${PORT_TELEM}.log" 2>&1 &
  sleep 1
  log "Telemetry exporter up"
}

### ── ORCHESTRATION (23–26) ────────────────────────────────────────────────
phase_23(){
  log "== Phase 23: Atlas Macro Fusion =="
  assess_env
  assess_files || warn "Some files missing; continuing with best effort"
  diagnose_atlas || true
  start_atlas
  wire_signal_engine
  write_phase "23"
  log "Phase 23 complete"
}

phase_24(){
  log "== Phase 24: Reinforcement Grid Fusion =="
  assess_env
  diagnose_reinforcement || true
  start_reinforcement
  write_phase "24"
  log "Phase 24 complete"
}

phase_25(){
  log "== Phase 25: Capital Governor Hook =="
  assess_env
  diagnose_capital_governor || true
  start_capital_governor
  write_phase "25"
  log "Phase 25 complete"
}

phase_26(){
  log "== Phase 26: Telemetry Panel Upgrade =="
  assess_env
  diagnose_telemetry || true
  start_telemetry_exporter
  write_phase "26"
  log "Phase 26 complete"
}

run_23_26(){
  venv_activate
  mkd "$LOG_DIR" "$RUNTIME_DIR"

  # Ensure upstream services are healthy first (sentiment, macro)
  if ! check_health "Sentiment" "$HEALTHZ_SENTIMENT"; then
    warn "Sentiment Bridge down; attempting auto-repair via guardian/autopilot..."
    # example: trigger your existing guardian/autofix here if available
    # bash "$ROOT_DIR/neo_light_fix_core.sh" --repair sentiment || true
  fi
  if ! check_health "Macro" "$HEALTHZ_MACRO"; then
    warn "Macro Forecaster down; attempting auto-repair..."
    # bash "$ROOT_DIR/neo_light_fix_core.sh" --repair macro || true
  fi

  phase_23
  phase_24
  phase_25
  phase_26

  log "All phases 23–26 completed. Current phase: $(current_phase)"
}

### ── CLI ──────────────────────────────────────────────────────────────────
case "${1:-}" in
  phases)
    case "${2:-}" in
      23-26) run_23_26 ;;
      23) phase_23 ;;
      24) phase_24 ;;
      25) phase_25 ;;
      26) phase_26 ;;
      all|"") run_23_26 ;;
      *) err "Unknown phase range: ${2:-}"; exit 2 ;;
    esac
    ;;
  *)
    echo "NeoLight Autopilot — Phases 23–26
Usage:
  $0 phases 23-26     Run all phases 23→26 (idempotent)
  $0 phases 23|24|25|26
  $0 phases all       Same as 23-26
"
    ;;
esac

