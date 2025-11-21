#!/usr/bin/env bash
# NeoLight Trading Stack Auto-Start
# Idempotent startup script for all trading components
# Designed to work with launchd for auto-restart on system boot/crash

set -euo pipefail

ROOT="${HOME}/neolight"
cd "$ROOT" || exit 1

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

LOCKFILE="/tmp/neolight_trading.lock"
LOG_FILE="$LOG_DIR/trading_autostart.log"

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
start_component() {
    local name="$1"
    local process_pattern="$2"
    local start_command="$3"
    local log_file="$LOG_DIR/${name}.log"
    
    if is_running "$process_pattern"; then
        log "✅ $name already running (PID: $(pgrep -f "$process_pattern" | head -1))"
        return 0
    fi
    
    log "🚀 Starting $name..."
    nohup bash -c "$start_command" >> "$log_file" 2>&1 &
    local pid=$!
    sleep 2
    
    if is_running "$process_pattern"; then
        log "✅ $name started successfully (PID: $(pgrep -f "$process_pattern" | head -1))"
        return 0
    else
        log "❌ $name failed to start"
        return 1
    fi
}

# Prevent duplicate launches with flock
exec 9>"$LOCKFILE"
if ! flock -n 9; then
    log "⚠️  Trading stack already starting/running - aborting"
    exit 0
fi

log "════════════════════════════════════════════════════"
log "🌐 Starting NeoLight Trading Stack"
log "════════════════════════════════════════════════════"

# Load secrets if available
if [ -f "$HOME/.neolight_secrets" ]; then
    source "$HOME/.neolight_secrets"
    log "🔐 Loaded environment secrets"
fi

# Also load .env file if it exists
if [ -f "$ROOT/.env" ]; then
    set -a
    source "$ROOT/.env"
    set +a
    log "🔐 Loaded .env file"
fi

# Component 1: Go Dashboard
start_component \
    "Go Dashboard" \
    "dashboard_go" \
    "cd $ROOT && ./dashboard_go" || log "⚠️  Go Dashboard start failed (may already be running)"

sleep 2

# Component 2: Market Intelligence Agent
start_component \
    "Market Intelligence" \
    "agents/market_intelligence.py" \
    "cd $ROOT && python3 agents/market_intelligence.py"

sleep 2

# Component 3: Strategy Research Agent
start_component \
    "Strategy Research" \
    "agents/strategy_research.py" \
    "cd $ROOT && python3 agents/strategy_research.py"

sleep 2

# Component 4: SmartTrader (Main Trading Loop)
start_component \
    "SmartTrader" \
    "trader/smart_trader.py" \
    "cd $ROOT && python3 trader/smart_trader.py"

sleep 3

log "════════════════════════════════════════════════════"
log "📊 Trading Stack Status Check"
log "════════════════════════════════════════════════════"

# Verify all components
FAILED=0

if is_running "dashboard_go"; then
    log "✅ Go Dashboard: RUNNING"
else
    log "❌ Go Dashboard: NOT RUNNING"
    FAILED=1
fi

if is_running "market_intelligence.py"; then
    log "✅ Market Intelligence: RUNNING"
else
    log "❌ Market Intelligence: NOT RUNNING"
    FAILED=1
fi

if is_running "strategy_research.py"; then
    log "✅ Strategy Research: RUNNING"
else
    log "❌ Strategy Research: NOT RUNNING"
    FAILED=1
fi

if is_running "smart_trader.py"; then
    log "✅ SmartTrader: RUNNING"
else
    log "❌ SmartTrader: NOT RUNNING"
    FAILED=1
fi

log "════════════════════════════════════════════════════"

if [ $FAILED -eq 0 ]; then
    log "🎉 All trading components running successfully!"
    log "📊 Dashboard: http://localhost:8100/health"
    log "📝 Logs: $LOG_DIR/"
    exit 0
else
    log "⚠️  Some components failed to start - check logs"
    exit 1
fi

# Release lock
flock -u 9

