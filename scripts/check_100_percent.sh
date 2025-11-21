#!/bin/bash
# Quick Status Check for 100% Capacity System

cd ~/neolight

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}  NEOLIGHT SYSTEM STATUS${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

# Core essentials
echo -e "${YELLOW}✅ Core Trading Components:${NC}"
CORE=$(ps aux | grep -E "(smart_trader\.py|market_intelligence\.py|strategy_research\.py|dashboard_go)" | grep -v grep | wc -l | xargs)
echo -e "   ${GREEN}$CORE/4 running${NC}"

echo -e "${YELLOW}✅ RL Learning System:${NC}"
RL=$(ps aux | grep -E "(rl_trainer\.py|rl_inference\.py)" | grep -v grep | wc -l | xargs)
echo -e "   ${GREEN}$RL/2 running (CRITICAL)${NC}"

echo -e "${YELLOW}✅ Rust Engines (Ultra-Fast):${NC}"
RUST=$(ps aux | grep -E "(risk_engine_rust)" | grep -v grep | wc -l | xargs)
echo -e "   ${GREEN}$RUST/2 running (100x faster)${NC}"

echo -e "${YELLOW}✅ Risk Management:${NC}"
RISK=$(ps aux | grep -E "(capital_governor|risk_governor|drawdown_guard|regime|performance_attribution)" | grep -v grep | wc -l | xargs)
echo -e "   ${GREEN}$RISK/5+ running${NC}"

echo -e "${YELLOW}✅ Portfolio & Allocation:${NC}"
PORTFOLIO=$(ps aux | grep -E "(allocator|portfolio|hrp)" | grep -v grep | wc -l | xargs)
echo -e "   ${GREEN}$PORTFOLIO/2+ running${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
TOTAL=$(ps aux | grep -v grep | grep -v "fseventsd\|appleeventsd\|distnoted" | grep -E "(smart_trader|market_intelligence|strategy_research|dashboard_go|rl_trainer|rl_inference|capital_governor|risk_governor|drawdown_guard|regime_detector|performance_attribution|risk_engine|events|allocator)" | wc -l | xargs)
echo -e "${GREEN}Total NeoLight Components: $TOTAL${NC}"

if [ "$TOTAL" -ge 16 ]; then
    echo -e "${GREEN}Status: WORLD-CLASS ✅${NC}"
    CAPACITY=$(echo "scale=1; $TOTAL * 100 / 18" | bc)
    echo -e "${GREEN}Practical Capacity: ${CAPACITY}%${NC}"
else
    echo -e "${YELLOW}Status: Some components down${NC}"
fi
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Service Endpoints:${NC}"
curl -s --max-time 1 http://localhost:8100/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ Dashboard:     http://localhost:8100${NC}" || echo -e "  ${YELLOW}❌ Dashboard${NC}"
curl -s --max-time 1 http://localhost:8300/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ Rust Risk:     http://localhost:8300${NC}" || echo -e "  ${YELLOW}❌ Rust Risk${NC}"
curl -s --max-time 1 http://localhost:8301/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ GPU Risk:      http://localhost:8301${NC}" || echo -e "  ${YELLOW}❌ GPU Risk${NC}"
curl -s --max-time 1 http://localhost:8500/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ Risk AI:       http://localhost:8500${NC}" || echo -e "  ${YELLOW}⚠️  Risk AI${NC}"

echo ""
if [ "$TOTAL" -ge 16 ]; then
    echo -e "${GREEN}🎉 System Ready for Autonomous Trading!${NC}"
else
    echo -e "${YELLOW}⚠️  Run: bash scripts/start_to_100_percent.sh${NC}"
fi
echo ""
echo -e "${BLUE}Quick commands:${NC}"
echo -e "  View logs:      ${BLUE}tail -f logs/*.log${NC}"
echo -e "  Trading status: ${BLUE}tail -f logs/smart_trader.log${NC}"
echo -e "  RL learning:    ${BLUE}tail -f logs/rl_trainer.log${NC}"
echo -e "  System audit:   ${BLUE}cat SYSTEM_AUDIT_REPORT.md${NC}"

