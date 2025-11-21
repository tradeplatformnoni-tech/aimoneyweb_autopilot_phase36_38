#!/usr/bin/env bash
# NeoLight Sports Data Ingestion Scheduler
# Runs daily at 3 AM to refresh NBA/Soccer history and odds snapshots

set -euo pipefail

ROOT="${HOME}/neolight"
PY="${ROOT}/venv/bin/python3"
LOG="${ROOT}/logs/sports_ingestion_scheduler.log"

mkdir -p "${ROOT}/logs"

export PYTHONPATH="${ROOT}"
export PYTHONUNBUFFERED=1

log() {
  echo "[$(date '+%F %T')] $*" | tee -a "$LOG"
}

run_ingestion() {
  local script="$1"
  shift
  local args="$*"
  
  log "🔄 Running $script $args"
  if cd "${ROOT}" && source venv/bin/activate && set -a && . ./.env && set +a && "$PY" "$script" $args >> "$LOG" 2>&1; then
    log "✅ $script completed successfully"
    return 0
  else
    log "❌ $script failed with exit code $?"
    return 1
  fi
}

check_data_freshness() {
  local dir="$1"
  local max_age_hours="$2"
  local name="$3"
  local sport="${4:-unknown}"
  
  if [[ ! -d "$dir" ]]; then
    log "⚠️ $name directory missing: $dir"
    "$PY" -c "from analytics.telegram_notifier import alert_missing_data; alert_missing_data('$sport', '$name', '$dir')" 2>/dev/null || true
    return 1
  fi
  
  local newest=$(find "$dir" -type f -name "*.json" -exec stat -f "%m %N" {} \; 2>/dev/null | sort -rn | head -n1 | awk '{print $1}')
  if [[ -z "$newest" ]]; then
    log "⚠️ No $name data files found in $dir"
    "$PY" -c "from analytics.telegram_notifier import alert_missing_data; alert_missing_data('$sport', '$name', '$dir')" 2>/dev/null || true
    return 1
  fi
  
  local now=$(date +%s)
  local age_hours=$(( (now - newest) / 3600 ))
  
  if (( age_hours > max_age_hours )); then
    log "⚠️ $name data is ${age_hours}h old (max: ${max_age_hours}h)"
    "$PY" -c "from analytics.telegram_notifier import alert_stale_data; alert_stale_data('$sport', '$name', $age_hours, $max_age_hours)" 2>/dev/null || true
    return 1
  fi
  
  log "✓ $name data is fresh (${age_hours}h old)"
  return 0
}

# Main ingestion loop
while true; do
  current_hour=$(date +%H)
  current_minute=$(date +%M)
  
  # Run at 3 AM daily
  if [[ "$current_hour" == "03" ]] && [[ "$current_minute" -lt "15" ]]; then
    log "========== Daily Sports Ingestion Started =========="
    
    # NBA ingestion
    if run_ingestion "${ROOT}/scripts/ingest_nba_data.py" "--seasons 2025,2024,2023"; then
      check_data_freshness "${ROOT}/data/sports_history/nba" 36 "NBA history" "nba" || true
      check_data_freshness "${ROOT}/data/odds_snapshots/nba" 24 "NBA odds" "nba" || true
      check_data_freshness "${ROOT}/data/sports_injuries" 24 "NBA injuries" "nba" || true
    else
      "$PY" -c "from analytics.telegram_notifier import alert_ingestion_failure; alert_ingestion_failure('nba', 'ingest_nba_data.py')" 2>/dev/null || true
    fi
    
    # Soccer ingestion
    if run_ingestion "${ROOT}/scripts/ingest_soccer_data.py" "--seasons 2025,2024,2023 --leagues EPL,LaLiga,SerieA,Bundesliga,Ligue1 --odds"; then
      check_data_freshness "${ROOT}/data/sports_history/soccer" 36 "Soccer history" "soccer" || true
      check_data_freshness "${ROOT}/data/odds_snapshots/soccer" 24 "Soccer odds" "soccer" || true
    else
      "$PY" -c "from analytics.telegram_notifier import alert_ingestion_failure; alert_ingestion_failure('soccer', 'ingest_soccer_data.py')" 2>/dev/null || true
    fi
    
    log "========== Daily Sports Ingestion Complete =========="
    
    # Sleep until next day to avoid multiple runs
    sleep 3600
  fi
  
  # Check every 15 minutes
  sleep 900
done

