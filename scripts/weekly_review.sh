#!/usr/bin/env bash
# NeoLight Weekly Review Script
# Run every Sunday to track training progress

set -euo pipefail

cd ~/neolight

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

WEEK_NUM=$(date +%U)

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  NEOLIGHT WEEKLY REVIEW - WEEK $WEEK_NUM${NC}"
echo -e "${BLUE}  $(date '+%B %d, %Y')${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# 1. Component Health
echo -e "${YELLOW}1. Component Status:${NC}"
bash scripts/check_100_percent.sh | grep -A 20 "NEOLIGHT SYSTEM STATUS"

# 2. RL Learning Progress
echo ""
echo -e "${YELLOW}2. RL Learning Progress:${NC}"
echo "Current Strategy Weights:"
cat runtime/rl_strategy_weights.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
weights = data['weights']
for k, v in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    bar = '█' * int(v * 50)
    print(f'  {k:25s} {v:6.1%} {bar}')
print(f'\nLast Updated: {data[\"timestamp\"]}')
" 2>/dev/null || echo "  RL weights file not found"

echo ""
echo "Recent RL Training:"
tail -10 logs/rl_trainer.log | grep -E "Training complete|Retraining" || echo "  No recent training"

# 3. Trading Performance (Last 7 Days)
echo ""
echo -e "${YELLOW}3. Trading Performance (Last 7 Days):${NC}"
python3 -c "
import pandas as pd
from datetime import datetime, timedelta
import os

pnl_file = 'state/pnl_history.csv'
if os.path.exists(pnl_file):
    df = pd.read_csv(pnl_file)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        week_ago = datetime.now() - timedelta(days=7)
        recent = df[df['date'] > week_ago]
    else:
        recent = df.tail(1000)  # Last 1000 trades as proxy
    
    if len(recent) > 0:
        wins = (recent['pnl'] > 0).sum() if 'pnl' in recent.columns else 0
        total = len(recent)
        win_rate = wins / total if total > 0 else 0
        total_pnl = recent['pnl'].sum() if 'pnl' in recent.columns else 0
        
        print(f'  Trades: {total}')
        print(f'  Win Rate: {win_rate:.1%}')
        print(f'  Total P&L: \${total_pnl:.2f}')
    else:
        print('  No recent trades')
else:
    print('  P&L history not found')
" 2>/dev/null || echo "  Unable to calculate stats"

# 4. Risk Metrics
echo ""
echo -e "${YELLOW}4. Risk Metrics:${NC}"
if [ -f "state/performance_metrics.csv" ]; then
    tail -1 state/performance_metrics.csv | awk -F',' '{
        printf "  Latest Equity: $%.2f\n", $3
        printf "  Drawdown: %.2f%%\n", $5
        printf "  30-Day Sharpe: %.2f\n", $6
        printf "  7-Day Win Rate: %.1f%%\n", $8 * 100
    }' 2>/dev/null || echo "  Performance metrics empty"
else
    echo "  Performance metrics not available"
fi

# 5. Current Portfolio State
echo ""
echo -e "${YELLOW}5. Current Portfolio:${NC}"
if [ -f "trader/state.json" ]; then
    python3 -c "
import json
with open('trader/state.json') as f:
    state = json.load(f)
print(f'  Cash: \${state[\"balances\"][\"USD\"]:.2f}')
print(f'  Positions: {len(state.get(\"positions\", {}))}')
if 'daily' in state:
    print(f'  Daily P&L: {state[\"daily\"].get(\"pnl_pct\", 0):.2f}%')
" 2>/dev/null
else
    echo "  State file not found"
fi

# 6. System Stability
echo ""
echo -e "${YELLOW}6. System Stability:${NC}"
COMPONENT_COUNT=$(ps aux | grep -E 'phases/|agents/|analytics/|ai/rl_' | grep -v grep | wc -l | xargs)
echo "  Active Components: $COMPONENT_COUNT"
echo "  Uptime: $(uptime | awk '{print $3, $4}' | sed 's/,//')"

ERROR_COUNT=$(grep -i "error\|critical" logs/*.log 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l | xargs)
echo "  Errors Today: $ERROR_COUNT"

WATCHDOG_RESTARTS=$(grep "restarted successfully" logs/trading_watchdog_comprehensive.log 2>/dev/null | grep "$(date +%Y-%m-%d)" | wc -l | xargs)
echo "  Watchdog Restarts Today: $WATCHDOG_RESTARTS"

# 7. Service Health
echo ""
echo -e "${YELLOW}7. Service Health:${NC}"
curl -s --max-time 1 http://localhost:8100/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ Dashboard (8100)${NC}" || echo "  ❌ Dashboard"
curl -s --max-time 1 http://localhost:8300/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ Rust Risk (8300)${NC}" || echo "  ❌ Rust Risk"
curl -s --max-time 1 http://localhost:8301/health > /dev/null 2>&1 && echo -e "  ${GREEN}✅ GPU Risk (8301)${NC}" || echo "  ❌ GPU Risk"

# 8. Recommendations
echo ""
echo -e "${YELLOW}8. This Week's Focus:${NC}"
if [ "$COMPONENT_COUNT" -lt 15 ]; then
    echo "  ⚠️  Start missing components: bash scripts/start_to_100_percent.sh"
fi
if [ "$ERROR_COUNT" -gt 50 ]; then
    echo "  ⚠️  High error count - review logs"
fi
if [ "$WATCHDOG_RESTARTS" -gt 10 ]; then
    echo "  ⚠️  Many restarts - investigate unstable components"
fi

echo "  ✅ Continue monitoring"
echo "  ✅ Review RL weight evolution"
echo "  ✅ Check performance trends"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Week $WEEK_NUM review complete! ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Save this report to: logs/weekly_reviews/week_${WEEK_NUM}_$(date +%Y%m%d).md${NC}"

