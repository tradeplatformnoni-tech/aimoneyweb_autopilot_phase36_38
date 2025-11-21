#!/bin/bash
# Run All New World-Class Phases
# ===============================
# Runs all newly created phases with world-class stability

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

start_phase() {
    local name="$1"
    local script="$2"
    local logfile="$ROOT/logs/${name}.log"
    
    if pgrep -f "$script" >/dev/null 2>&1; then
        log "✅ $name already running"
        return 0
    fi
    
    log "🚀 Starting $name..."
    nohup python3 "$script" >> "$logfile" 2>&1 &
    sleep 2
    
    if pgrep -f "$script" >/dev/null 2>&1; then
        log "✅ $name started successfully (PID: $(pgrep -f "$script" | head -n1))"
        return 0
    else
        error "$name failed to start - check $logfile"
        return 1
    fi
}

log "🚀 Starting all new world-class phases..."

# Phase 1-50: Foundation
start_phase "foundation" "$ROOT/phases/phase_1_50_foundation.py"

# Phase 51-90: Core Trading
start_phase "core_trading" "$ROOT/phases/phase_51_90_core_trading.py"

# Phase 101-130: Advanced Trading
start_phase "advanced_trading" "$ROOT/phases/phase_101_130_advanced_trading.py"

# Phase 141-200: Trading Extensions
start_phase "trading_extensions" "$ROOT/phases/phase_141_200_trading_extensions.py"

# Phase 241-260: Analytics
start_phase "analytics" "$ROOT/phases/phase_241_260_analytics.py"

# Phase 281-300: Risk Extensions
start_phase "risk_extensions" "$ROOT/phases/phase_281_300_risk_extensions.py"

# Phase 341-390: Replay Extensions
start_phase "replay_extensions" "$ROOT/phases/phase_341_390_replay_extensions.py"

# Phase 461-900: Intelligence Extensions
start_phase "intelligence_extensions" "$ROOT/phases/phase_461_900_intelligence_extensions.py"

log "✅ All new phases started!"
log "📊 Check logs in $ROOT/logs/ for each phase"

# Show running processes
log "📋 Running phase processes:"
ps aux | grep -E "phase_(1_50|51_90|101_130|141_200|241_260|281_300|341_390|461_900)" | grep -v grep || echo "No processes found"
