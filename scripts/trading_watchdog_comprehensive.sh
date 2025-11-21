#!/usr/bin/env bash
# NeoLight Comprehensive Trading Watchdog - World-Class Edition
# Monitors and auto-restarts ALL critical trading components
# Checks every 30 seconds

set -euo pipefail

ROOT="${HOME}/neolight"
cd "$ROOT" || exit 1

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/trading_watchdog_comprehensive.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if a process is running by name
is_running() {
    local process_pattern="$1"
    pgrep -f "$process_pattern" > /dev/null 2>&1
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

log "🐕 Comprehensive Trading Watchdog started - monitoring every 30 seconds"

# Watchdog loop - runs forever
while true; do
    # ===== CORE TRADING COMPONENTS =====
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
    
    # ===== RL/ML LEARNING SYSTEMS =====
    start_if_needed \
        "RL Trainer" \
        "ai/rl_trainer.py --loop" \
        "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 ai/rl_trainer.py --loop"
    
    start_if_needed \
        "RL Inference" \
        "ai/rl_inference.py --loop" \
        "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 ai/rl_inference.py --loop --interval 300"
    
    start_if_needed \
        "RL Performance Tracker" \
        "analytics/rl_performance.py" \
        "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 analytics/rl_performance.py --report"
    
    # ===== RISK MANAGEMENT =====
    start_if_needed \
        "Risk Governor" \
        "phase_101_120_risk_governor.sh" \
        "cd $ROOT && bash phases/phase_101_120_risk_governor.sh"
    
    start_if_needed \
        "Drawdown Guard" \
        "phase_121_130_drawdown_guard.sh" \
        "cd $ROOT && bash phases/phase_121_130_drawdown_guard.sh"
    
    start_if_needed \
        "Capital Governor" \
        "phase_5700_5900_capital_governor.py" \
        "cd $ROOT && python3 agents/phase_5700_5900_capital_governor.py"
    
    # ===== PORTFOLIO OPTIMIZATION =====
    start_if_needed \
        "Portfolio Optimizer" \
        "phase_2500_2700_portfolio_optimization.py" \
        "cd $ROOT && python3 phases/phase_2500_2700_portfolio_optimization.py"
    
    start_if_needed \
        "Hierarchical Risk Parity" \
        "hierarchical_risk_parity_runner.py" \
        "cd $ROOT && python3 analytics/hierarchical_risk_parity_runner.py"
    
    # ===== ADVANCED ANALYTICS =====
    start_if_needed \
        "Regime Detector" \
        "agents/regime_detector.py" \
        "cd $ROOT && python3 agents/regime_detector.py"
    
    start_if_needed \
        "Performance Attribution" \
        "agents/performance_attribution.py" \
        "cd $ROOT && python3 agents/performance_attribution.py"
    
    # ===== RUST RISK ENGINES =====
    start_if_needed \
        "Rust Risk Engine" \
        "target/release/risk_engine_rust" \
        "cd $ROOT/risk_engine_rust && ./target/release/risk_engine_rust"
    
    start_if_needed \
        "GPU Risk Engine" \
        "target/release/risk_engine_rust_gpu" \
        "cd $ROOT/risk_engine_rust_gpu && ./target/release/risk_engine_rust_gpu"
    
    # ===== AI RISK SERVER =====
    start_if_needed \
        "Risk AI Server" \
        "ai/risk_ai_server.py" \
        "cd $ROOT && python3 ai/risk_ai_server.py"
    
    # ===== ML PIPELINE =====
    start_if_needed \
        "ML Pipeline" \
        "agents/ml_pipeline.py" \
        "cd $ROOT && python3 agents/ml_pipeline.py"
    
    # ===== ADVANCED PHASES =====
    start_if_needed \
        "Events System" \
        "phases/phase_3900_4100_events.py" \
        "cd $ROOT && python3 phases/phase_3900_4100_events.py"
    
    start_if_needed \
        "Execution Optimizer" \
        "phases/phase_4100_4300_execution.py" \
        "cd $ROOT && python3 phases/phase_4100_4300_execution.py"
    
    # Wait 30 seconds before next check
    sleep 30
done

