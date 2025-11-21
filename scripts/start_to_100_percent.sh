#!/usr/bin/env bash
# NeoLight - Reach 100% Capacity
# Starts ALL missing components to achieve full system utilization

set -euo pipefail

ROOT="${HOME}/neolight"
cd "$ROOT" || exit 1

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  NeoLight - Reaching 100% Capacity${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""

# Load secrets
if [ -f "$HOME/.neolight_secrets" ]; then
    source "$HOME/.neolight_secrets"
fi

# Check if already running before starting
start_component() {
    local name="$1"
    local pattern="$2"
    local command="$3"
    local log_file="$4"
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name already running${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🚀 Starting $name...${NC}"
    nohup bash -c "$command" > "$log_file" 2>&1 &
    sleep 2
    
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name started (PID: $(pgrep -f "$pattern" | head -1))${NC}"
    else
        echo -e "${YELLOW}⚠️  $name may need a moment to start...${NC}"
    fi
}

echo -e "${YELLOW}Step 1: Core Trading Components${NC}"
start_component "SmartTrader" "trader/smart_trader.py" \
    "cd $ROOT && python3 trader/smart_trader.py" \
    "$LOG_DIR/smart_trader.log"

start_component "Market Intelligence" "agents/market_intelligence.py" \
    "cd $ROOT && python3 agents/market_intelligence.py" \
    "$LOG_DIR/market_intelligence.log"

start_component "Strategy Research" "agents/strategy_research.py" \
    "cd $ROOT && python3 agents/strategy_research.py" \
    "$LOG_DIR/strategy_research.log"

start_component "Go Dashboard" "dashboard_go" \
    "cd $ROOT && ./dashboard_go" \
    "$LOG_DIR/dashboard_go.log"

echo ""
echo -e "${YELLOW}Step 2: RL/ML Learning Systems${NC}"
start_component "RL Trainer" "ai/rl_trainer.py --loop" \
    "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 ai/rl_trainer.py --loop" \
    "$LOG_DIR/rl_trainer.log"

start_component "RL Inference" "ai/rl_inference.py --loop" \
    "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 ai/rl_inference.py --loop --interval 300" \
    "$LOG_DIR/rl_inference.log"

start_component "RL Performance" "analytics/rl_performance.py" \
    "cd $ROOT && PYTHONPATH=$ROOT:\$PYTHONPATH python3 analytics/rl_performance.py --loop" \
    "$LOG_DIR/rl_performance.log"

start_component "ML Pipeline" "agents/ml_pipeline.py" \
    "cd $ROOT && python3 agents/ml_pipeline.py" \
    "$LOG_DIR/ml_pipeline.log"

echo ""
echo -e "${YELLOW}Step 3: Risk Management Stack${NC}"
start_component "Risk Governor" "phase_101_120_risk_governor" \
    "cd $ROOT && bash phases/phase_101_120_risk_governor.sh" \
    "$LOG_DIR/risk_governor.log"

start_component "Drawdown Guard" "phase_121_130_drawdown_guard" \
    "cd $ROOT && bash phases/phase_121_130_drawdown_guard.sh" \
    "$LOG_DIR/drawdown_guard.log"

start_component "Capital Governor" "phase_5700_5900_capital_governor" \
    "cd $ROOT && python3 agents/phase_5700_5900_capital_governor.py" \
    "$LOG_DIR/capital_governor.log"

start_component "Rust Risk Engine" "target/release/risk_engine_rust[^_]" \
    "cd $ROOT/risk_engine_rust && ./target/release/risk_engine_rust" \
    "$LOG_DIR/risk_engine_rust.log"

start_component "GPU Risk Engine" "target/release/risk_engine_rust_gpu" \
    "cd $ROOT/risk_engine_rust_gpu && ./target/release/risk_engine_rust_gpu" \
    "$LOG_DIR/risk_engine_rust_gpu.log"

start_component "Risk AI Server" "ai/risk_ai_server.py" \
    "cd $ROOT && python3 ai/risk_ai_server.py" \
    "$LOG_DIR/risk_ai_server.log"

start_component "Regime Detector" "agents/regime_detector.py" \
    "cd $ROOT && python3 agents/regime_detector.py" \
    "$LOG_DIR/regime_detector.log"

start_component "Performance Attribution" "agents/performance_attribution.py" \
    "cd $ROOT && python3 agents/performance_attribution.py" \
    "$LOG_DIR/performance_attribution.log"

echo ""
echo -e "${YELLOW}Step 4: Portfolio Optimization${NC}"
start_component "Portfolio Optimizer" "phase_2500_2700_portfolio_optimization" \
    "cd $ROOT && python3 phases/phase_2500_2700_portfolio_optimization.py" \
    "$LOG_DIR/portfolio_opt.log"

start_component "HRP Optimizer" "hierarchical_risk_parity.py" \
    "cd $ROOT && python3 analytics/hierarchical_risk_parity.py" \
    "$LOG_DIR/hrp.log"

echo ""
echo -e "${YELLOW}Step 5: Advanced Phases${NC}"
start_component "Events System" "phase_3900_4100_events.py" \
    "cd $ROOT && python3 phases/phase_3900_4100_events.py" \
    "$LOG_DIR/events_system.log"

start_component "Execution Optimizer" "phase_4100_4300_execution.py" \
    "cd $ROOT && python3 phases/phase_4100_4300_execution.py" \
    "$LOG_DIR/execution_opt.log"

start_component "Allocator" "phase_131_140_allocator.py" \
    "cd $ROOT && python3 phases/phase_131_140_allocator.py" \
    "$LOG_DIR/allocator.log"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 6: Final Verification${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
sleep 5

# Count components by category
CORE=$(ps aux | grep -E "(smart_trader\.py|market_intelligence\.py|strategy_research\.py|dashboard_go)" | grep -v grep | wc -l | xargs)
RLML=$(ps aux | grep -E "(rl_trainer|rl_inference|rl_performance|ml_pipeline)" | grep -v grep | wc -l | xargs)
RISK=$(ps aux | grep -E "(capital_governor|risk_governor|drawdown_guard|regime_detector|performance_attribution|risk_engine|risk_ai)" | grep -v grep | wc -l | xargs)
PORTFOLIO=$(ps aux | grep -E "(portfolio.*optim|hierarchical_risk|allocator)" | grep -v grep | wc -l | xargs)
ADVANCED=$(ps aux | grep -E "(events\.py|execution\.py)" | grep -v grep | wc -l | xargs)
INFRA=$(ps aux | grep -E "(watchdog_comprehensive)" | grep -v grep | wc -l | xargs)

TOTAL=$((CORE + RLML + RISK + PORTFOLIO + ADVANCED + INFRA))

echo -e "${GREEN}Core Trading: $CORE/4${NC}"
echo -e "${GREEN}RL/ML Systems: $RLML/4${NC}"
echo -e "${GREEN}Risk Management: $RISK/8${NC}"
echo -e "${GREEN}Portfolio Optimization: $PORTFOLIO/3${NC}"
echo -e "${GREEN}Advanced Phases: $ADVANCED/2${NC}"
echo -e "${GREEN}Infrastructure: $INFRA/1${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}Total Components: $TOTAL${NC}"
CAPACITY=$(echo "scale=1; $TOTAL * 100 / 22" | bc)
echo -e "${GREEN}System Capacity: ${CAPACITY}%${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"

# Health checks
echo ""
echo -e "${YELLOW}Service Health Checks:${NC}"
curl -s http://localhost:8100/health > /dev/null && echo -e "${GREEN}✅ Go Dashboard (8100)${NC}" || echo -e "${YELLOW}⚠️  Go Dashboard${NC}"
curl -s http://localhost:8300/health > /dev/null && echo -e "${GREEN}✅ Rust Risk Engine (8300)${NC}" || echo -e "${YELLOW}⚠️  Rust Risk Engine${NC}"
curl -s http://localhost:8301/health > /dev/null && echo -e "${GREEN}✅ GPU Risk Engine (8301)${NC}" || echo -e "${YELLOW}⚠️  GPU Risk Engine${NC}"
curl -s http://localhost:8500/health > /dev/null && echo -e "${GREEN}✅ Risk AI Server (8500)${NC}" || echo -e "${YELLOW}⚠️  Risk AI Server${NC}"

echo ""
if [ "$CAPACITY" = "100.0" ] || [ $(echo "$CAPACITY >= 95" | bc) -eq 1 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🎊 SYSTEM AT ${CAPACITY}% CAPACITY - WORLD-CLASS! 🎊${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
else
    echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}System at ${CAPACITY}% - Review logs for any failures${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"
fi

echo ""
echo -e "${BLUE}Monitor logs: tail -f logs/*.log${NC}"
echo -e "${BLUE}Check status: ps aux | grep -E '(rl_|risk_|portfolio)' | grep -v grep${NC}"

