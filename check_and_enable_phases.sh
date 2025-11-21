#!/bin/bash
# Check which phases are currently running and enable missing ones

cd ~/neolight || exit 1

echo "======================================================================"
echo "🔍 Checking Phase Status"
echo "======================================================================"
echo ""

# Function to check if a process is running
check_running() {
    local name="$1"
    local pattern="$2"
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        echo "✅ $name: RUNNING"
        return 0
    else
        echo "❌ $name: NOT RUNNING"
        return 1
    fi
}

# Function to check log file recency (within last hour)
check_log_recent() {
    local log_file="$1"
    if [ -f "$log_file" ]; then
        local age=$(($(date +%s) - $(stat -f %m "$log_file" 2>/dev/null || echo 0)))
        if [ $age -lt 3600 ]; then
            echo "✅ Log active (updated $((age/60)) min ago)"
            return 0
        else
            echo "⚠️  Log stale (updated $((age/3600)) hours ago)"
            return 1
        fi
    else
        echo "❌ No log file"
        return 1
    fi
}

echo "📊 Checking Currently Enabled Phases:"
echo ""

# Check Phase 301-340: Equity Replay
echo "1. Phase 301-340: Equity Replay"
check_running "Equity Replay" "phase_301_340_equity_replay"
check_log_recent "logs/equity_replay.log"
echo ""

# Check Phase 900-1100: Atlas Integration (integrated in orchestrator)
echo "2. Phase 900-1100: Atlas Integration & Telemetry"
check_running "Atlas/Telemetry" "intelligence_orchestrator|atlas"
check_log_recent "logs/intelligence_orchestrator.log"
echo ""

# Check Phase 1100-1300: AI Learning & Backtesting
echo "3. Phase 1100-1300: AI Learning & Backtesting"
check_running "Backtesting" "replay_engine|backtest"
check_log_recent "logs/replay_engine.log"
echo ""

# Check Phase 1500-1800: ML Pipeline
echo "4. Phase 1500-1800: ML Pipeline"
check_running "ML Pipeline" "ml_pipeline"
check_log_recent "logs/ml_pipeline.log"
echo ""

# Check Phase 1800-2000: Performance Attribution
echo "5. Phase 1800-2000: Performance Attribution"
check_running "Performance Attribution" "performance_attribution"
check_log_recent "logs/performance_attribution.log"
echo ""

# Check Phase 2000-2300: Regime Detection
echo "6. Phase 2000-2300: Regime Detection"
check_running "Regime Detection" "regime_detector"
check_log_recent "logs/regime_detector.log"
echo ""

# Check Phase 2300-2500: Meta-Metrics Dashboard
echo "7. Phase 2300-2500: Meta-Metrics Dashboard"
check_running "Dashboard" "dashboard|uvicorn.*dashboard"
check_log_recent "logs/dashboard.log"
echo ""

# Check Phase 2500-2700: Portfolio Optimization
echo "8. Phase 2500-2700: Portfolio Optimization"
check_running "Portfolio Optimization" "phase_2500_2700_portfolio_optimization"
check_log_recent "logs/portfolio_optimization.log"
echo ""

# Check Phase 2700-2900: Advanced Risk Management
echo "9. Phase 2700-2900: Advanced Risk Management"
check_running "Risk Management" "phase_2700_2900_risk_management"
check_log_recent "logs/risk_management.log"
echo ""

# Check Phase 3100-3300: Enhanced Signal Generation (integrated in smart_trader)
echo "10. Phase 3100-3300: Enhanced Signal Generation"
check_running "Signal Generation" "smart_trader"
check_log_recent "logs/smart_trader.log"
echo ""

# Check Phase 3300-3500: Kelly Criterion
echo "11. Phase 3300-3500: Kelly Criterion & Position Sizing"
check_running "Kelly Sizing" "phase_3300_3500_kelly"
check_log_recent "logs/kelly_sizing.log"
echo ""

# Check Phase 3500-3700: Multi-Strategy Framework
echo "12. Phase 3500-3700: Multi-Strategy Framework"
check_running "Strategy Manager" "strategy_manager"
check_log_recent "logs/strategy_manager.log"
echo ""

# Check Phase 3700-3900: Reinforcement Learning
echo "13. Phase 3700-3900: Reinforcement Learning"
check_running "RL Enhanced" "phase_3700_3900_rl|rl_enhanced"
check_log_recent "logs/rl_enhanced.log"
echo ""

# Check Phase 3900-4100: Event-Driven Architecture
echo "14. Phase 3900-4100: Event-Driven Architecture"
check_running "Event Driven" "phase_3900_4100_events|event_driven"
check_log_recent "logs/event_driven.log"
echo ""

# Check Phase 4100-4300: Advanced Execution Algorithms
echo "15. Phase 4100-4300: Advanced Execution Algorithms"
check_running "Execution Algorithms" "phase_4100_4300_execution|execution_algorithms"
check_log_recent "logs/execution_algorithms.log"
echo ""

# Check Phase 4300-4500: Portfolio Analytics
echo "16. Phase 4300-4500: Portfolio Analytics & Attribution"
check_running "Portfolio Analytics" "phase_4300_4500_analytics|portfolio_analytics"
check_log_recent "logs/portfolio_analytics.log"
echo ""

# Check Phase 4500-4700: Alternative Data Integration
echo "17. Phase 4500-4700: Alternative Data Integration"
check_running "Alt Data" "phase_4500_4700_alt_data|alt_data"
check_log_recent "logs/alt_data.log"
echo ""

echo "======================================================================"
echo "📋 Summary: Phases that need to be enabled"
echo "======================================================================"

