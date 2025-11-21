#!/usr/bin/env bash
set -Eeuo pipefail
LABEL="phase_281_300_ops_hardening"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/logs"; mkdir -p "$LOG_DIR"
RUN_DIR="${ROOT}/runtime"; mkdir -p "$RUN_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/${LABEL}_${STAMP}.log"

log(){ printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "$LOG"; }

# Log retention: keep 7d by default
find "$LOG_DIR" -type f -mtime +7 -delete 2>/dev/null || true

# Ensure metrics exporter reachable
if ! curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:9501/metrics" | grep -q "200"; then
  log "⚠️  Metrics exporter not reachable on :9501"
fi

# Validate venv health (optionally auto-repair hook you installed earlier)
if [ ! -x "$HOME/.neolight_env/neo_guardian_autorepair.sh" ]; then
  log "ℹ️ No Smart-Activator Companion found at ~/.neolight_env/neo_guardian_autorepair.sh (optional)"
fi

# Cost tips (notes only; run manually as desired):
# - Fly.io: scale down or suspend idle apps to control spend.
#   Example commands (replace with your app name):
#     fly scale count 0
#     fly apps suspend <app-name>   # (if supported)
# - Reduce telemetry frequency by increasing sleep intervals above if needed.

log "🛡️ Ops hardening pass complete"
sleep 1800
exec "$0" # loop forever with tidy checks

