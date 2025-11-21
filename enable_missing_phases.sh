#!/bin/bash
# Direct startup script for missing phases (bypasses guardian if needed)
# Usage: bash enable_missing_phases.sh [phase_name|all]

cd ~/neolight || exit 1

ROOT="$HOME/neolight"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
PY="${VENV}/bin/python"
export PYTHONPATH="$ROOT"
export PATH="$VENV/bin:$PATH"

mkdir -p "$LOGS"

# Color helpers
note(){ echo "🧠 $*"; }
ok(){ echo "✅ $*"; }
warn(){ echo "⚠️  $*"; }
err(){ echo "❌ $*"; }

# Function to start a phase
start_phase() {
    local name="$1"
    local script="$2"
    local log="$3"
    local pattern="$4"
    
    # Check if already running
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        ok "$name is already running"
        return 0
    fi
    
    # Check if script exists
    if [ ! -f "$ROOT/$script" ]; then
        err "$name script not found: $script"
        return 1
    fi
    
    # Start the phase
    note "Starting $name..."
    nohup bash -c "
        cd '$ROOT'
        export PYTHONPATH='$ROOT'
        source '$VENV/bin/activate' 2>/dev/null || true
        $PY $script >> '$LOGS/$log' 2>&1
    " >/dev/null 2>&1 &
    
    local pid=$!
    sleep 2
    
    # Verify it's running
    if kill -0 $pid 2>/dev/null || pgrep -f "$pattern" >/dev/null 2>&1; then
        ok "$name started (PID: $pid)"
        return 0
    else
        err "$name failed to start (check $LOGS/$log)"
        return 1
    fi
}

# Phase definitions
declare -A PHASES
PHASES["equity_replay"]="phases/phase_301_340_equity_replay.py|equity_replay.log|phase_301_340_equity_replay|Phase 301-340: Equity Replay"
PHASES["strategy_backtesting"]="analytics/strategy_backtesting.py|strategy_backtesting.log|strategy_backtesting|Phase 1100-1300: AI Learning & Backtesting"
PHASES["portfolio_optimization"]="phases/phase_2500_2700_portfolio_optimization.py|portfolio_optimization.log|phase_2500_2700_portfolio_optimization|Phase 2500-2700: Portfolio Optimization"
PHASES["risk_management"]="phases/phase_2700_2900_risk_management.py|risk_management.log|phase_2700_2900_risk_management|Phase 2700-2900: Advanced Risk Management"
PHASES["kelly_sizing"]="phases/phase_3300_3500_kelly.py|kelly_sizing.log|phase_3300_3500_kelly|Phase 3300-3500: Kelly Criterion"
PHASES["rl_enhanced"]="phases/phase_3700_3900_rl.py|rl_enhanced.log|phase_3700_3900_rl|Phase 3700-3900: Reinforcement Learning"
PHASES["event_driven"]="phases/phase_3900_4100_events.py|event_driven.log|phase_3900_4100_events|Phase 3900-4100: Event-Driven Architecture"
PHASES["execution_algorithms"]="phases/phase_4100_4300_execution.py|execution_algorithms.log|phase_4100_4300_execution|Phase 4100-4300: Advanced Execution Algorithms"
PHASES["portfolio_analytics"]="phases/phase_4300_4500_analytics.py|portfolio_analytics.log|phase_4300_4500_analytics|Phase 4300-4500: Portfolio Analytics"
PHASES["alt_data"]="phases/phase_4500_4700_alt_data.py|alt_data.log|phase_4500_4700_alt_data|Phase 4500-4700: Alternative Data Integration"

# Main logic
if [ "$1" = "all" ] || [ -z "$1" ]; then
    echo "======================================================================"
    echo "🚀 Starting All Missing Phases"
    echo "======================================================================"
    echo ""
    
    started=0
    failed=0
    skipped=0
    
    for phase_key in "${!PHASES[@]}"; do
        IFS='|' read -r script log pattern name <<< "${PHASES[$phase_key]}"
        if start_phase "$name" "$script" "$log" "$pattern"; then
            ((started++))
        else
            if pgrep -f "$pattern" >/dev/null 2>&1; then
                ((skipped++))
            else
                ((failed++))
            fi
        fi
    done
    
    echo ""
    echo "======================================================================"
    echo "📋 Summary"
    echo "======================================================================"
    echo "✅ Started: $started"
    echo "⏭️  Skipped (already running): $skipped"
    echo "❌ Failed: $failed"
    echo ""
    
elif [ -n "${PHASES[$1]}" ]; then
    # Start specific phase
    IFS='|' read -r script log pattern name <<< "${PHASES[$1]}"
    start_phase "$name" "$script" "$log" "$pattern"
else
    err "Unknown phase: $1"
    echo ""
    echo "Available phases:"
    for phase_key in "${!PHASES[@]}"; do
        IFS='|' read -r script log pattern name <<< "${PHASES[$phase_key]}"
        echo "  - $phase_key: $name"
    done
    echo ""
    echo "Usage: $0 [phase_name|all]"
    exit 1
fi

