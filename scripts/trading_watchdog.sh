#!/usr/bin/env bash
# NeoLight Trading Watchdog - Continuous Monitoring & Auto-Restart
# Monitors trading components and restarts them if they crash

set -euo pipefail

ROOT="${HOME}/neolight"
cd "$ROOT" || exit 1

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/trading_watchdog.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if a process is running by name
is_running() {
    local process_name="$1"
    pgrep -f "$process_name" > /dev/null 2>&1
}

# Start a component if not already running
start_if_needed() {
    local name="$1"
    local process_pattern="$2"
    local start_command="$3"
    local log_file="$LOG_DIR/${name}.log"
    
    if is_running "$process_pattern"; then
        return 0  # Already running, no need to log
    fi
    
    log "⚠️  $name is DOWN - restarting..."
    nohup bash -c "$start_command" >> "$log_file" 2>&1 &
    sleep 3
    
    if is_running "$process_pattern"; then
        log "✅ $name restarted successfully (PID: $(pgrep -f "$process_pattern" | head -1))"
    else
        log "❌ $name failed to restart"
    fi
}

# Load secrets if available
if [ -f "$HOME/.neolight_secrets" ]; then
    source "$HOME/.neolight_secrets"
fi

log "🐕 Trading Watchdog started - monitoring components every 30 seconds"

# Watchdog loop - runs forever
while true; do
    # Check and restart each component if needed
    start_if_needed \
        "Go Dashboard" \
        "dashboard_go" \
        "cd $ROOT && ./dashboard_go"
    
    start_if_needed \
        "Market Intelligence" \
        "agents/market_intelligence.py" \
        "cd $ROOT && python3 agents/market_intelligence.py"
    
    start_if_needed \
        "Strategy Research" \
        "agents/strategy_research.py" \
        "cd $ROOT && python3 agents/strategy_research.py"
    
    start_if_needed \
        "SmartTrader" \
        "trader/smart_trader.py" \
        "cd $ROOT && python3 trader/smart_trader.py"
    
    # Wait 30 seconds before next check
    sleep 30
done

