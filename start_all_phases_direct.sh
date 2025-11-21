#!/bin/bash
# Direct phase startup that bypasses shell issues
set -e

cd ~/neolight
export PYTHONPATH="$HOME/neolight"
export PATH="$HOME/neolight/venv/bin:$PATH"

# Source venv if it exists
if [ -f "$HOME/neolight/venv/bin/activate" ]; then
    source "$HOME/neolight/venv/bin/activate"
fi

PYTHON="${HOME}/neolight/venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "======================================================================"
echo "🚀 Starting All Missing Phases (Direct)"
echo "======================================================================"
echo ""

# Phase scripts to start
PHASES=(
    "phases/phase_301_340_equity_replay.py:equity_replay.log:phase_301_340_equity_replay"
    "phases/phase_2500_2700_portfolio_optimization.py:portfolio_optimization.log:phase_2500_2700_portfolio_optimization"
    "phases/phase_2700_2900_risk_management.py:risk_management.log:phase_2700_2900_risk_management"
    "phases/phase_3300_3500_kelly.py:kelly_sizing.log:phase_3300_3500_kelly"
    "phases/phase_3700_3900_rl.py:rl_enhanced.log:phase_3700_3900_rl"
    "phases/phase_3900_4100_events.py:event_driven.log:phase_3900_4100_events"
    "phases/phase_4100_4300_execution.py:execution_algorithms.log:phase_4100_4300_execution"
    "phases/phase_4300_4500_analytics.py:portfolio_analytics.log:phase_4300_4500_analytics"
    "phases/phase_4500_4700_alt_data.py:alt_data.log:phase_4500_4700_alt_data"
)

started=0
skipped=0
failed=0

for phase_info in "${PHASES[@]}"; do
    IFS=':' read -r script log pattern <<< "$phase_info"
    
    # Check if already running
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        echo "✅ $script: Already running"
        ((skipped++))
        continue
    fi
    
    # Check if script exists
    if [ ! -f "$script" ]; then
        echo "⚠️  $script: Not found"
        ((failed++))
        continue
    fi
    
    # Start the phase
    echo "🚀 Starting $script..."
    nohup "$PYTHON" "$script" >> "logs/$log" 2>&1 &
    pid=$!
    sleep 2
    
    # Verify it started
    if kill -0 $pid 2>/dev/null || pgrep -f "$pattern" >/dev/null 2>&1; then
        echo "✅ $script: Started (PID: $pid)"
        ((started++))
    else
        echo "❌ $script: Failed to start (check logs/$log)"
        ((failed++))
    fi
done

echo ""
echo "======================================================================"
echo "📋 Summary"
echo "======================================================================"
echo "✅ Started: $started"
echo "⏭️  Skipped: $skipped"
echo "❌ Failed: $failed"
echo ""

