#!/bin/bash
# NeoLight Quick Status Dashboard
# Shows comprehensive trading system status at a glance
# Usage: ./scripts/quick_status.sh [--watch] [--refresh SECONDS]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
REFRESH_INTERVAL=5
WATCH_MODE=false
PROJECT_ROOT="${HOME}/neolight"
LOG_FILE="${PROJECT_ROOT}/logs/smart_trader.log"
STATE_FILE="${PROJECT_ROOT}/state/smart_trader_state.json"
RUNTIME_DIR="${PROJECT_ROOT}/runtime"

# Parse arguments
for arg in "$@"; do
    if [[ "$arg" == "--watch" ]] || [[ "$arg" == "-w" ]]; then
        WATCH_MODE=true
    elif [[ "$arg" =~ --refresh=([0-9]+) ]]; then
        REFRESH_INTERVAL="${BASH_REMATCH[1]}"
    elif [[ "$arg" == "--refresh" ]] && [[ -n "${2:-}" ]] && [[ "${2:-}" =~ ^[0-9]+$ ]]; then
        REFRESH_INTERVAL="$2"
    fi
done

# Helper functions
print_header() {
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}  ${BOLD}NeoLight Trading System Status${NC}  $(date '+%Y-%m-%d %H:%M:%S')  ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_agent_running() {
    if pgrep -f "smart_trader.py" > /dev/null; then
        PID=$(pgrep -f "smart_trader.py" | head -1)
        UPTIME=$(ps -p "$PID" -o etime= 2>/dev/null | xargs || echo "unknown")
        echo -e "${GREEN}✅ RUNNING${NC} (PID: $PID, Uptime: $UPTIME)"
        return 0
    else
        echo -e "${RED}❌ STOPPED${NC}"
        return 1
    fi
}

get_portfolio_value() {
    if [[ -f "$STATE_FILE" ]]; then
        python3 -c "
import json
import sys
try:
    with open('$STATE_FILE') as f:
        state = json.load(f)
    broker_state = state.get('broker', {})
    cash = float(broker_state.get('cash', 0))
    equity = float(broker_state.get('equity', 0))
    portfolio = cash + equity
    print(f'{portfolio:.2f}')
except Exception as e:
    print('0.00', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "100000.00"
    else
        echo "100000.00"  # Default starting value
    fi
}

get_positions() {
    if [[ -f "$STATE_FILE" ]]; then
        python3 -c "
import json
import sys
try:
    with open('$STATE_FILE') as f:
        state = json.load(f)
    positions = state.get('broker', {}).get('positions', {})
    count = len([p for p in positions.values() if float(p.get('qty', 0)) > 1e-6])
    print(count)
except Exception:
    print(0, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

get_recent_trades() {
    if [[ -f "$LOG_FILE" ]]; then
        grep -E "ORDER SUBMITTED|PAPER (BUY|SELL) EXECUTED" "$LOG_FILE" 2>/dev/null | tail -5 || echo ""
    else
        echo ""
    fi
}

get_circuit_breaker_status() {
    if [[ -f "$LOG_FILE" ]]; then
        grep "CIRCUIT BREAKER STATUS" "$LOG_FILE" 2>/dev/null | tail -1 || echo ""
    else
        echo ""
    fi
}

get_recent_errors() {
    if [[ -f "$LOG_FILE" ]]; then
        grep -E "ERROR|WARNING.*BLOCKED|FAILED" "$LOG_FILE" 2>/dev/null | tail -10 || echo ""
    else
        echo ""
    fi
}

get_system_health() {
    # CPU usage
    CPU=$(top -l 1 2>/dev/null | grep "CPU usage" | awk '{print $3}' | sed 's/%//' 2>/dev/null || echo "0")
    # Memory usage (simplified)
    MEM_FREE=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | sed 's/\.//' || echo "0")
    MEM_ACTIVE=$(vm_stat 2>/dev/null | grep "Pages active" | awk '{print $3}' | sed 's/\.//' || echo "0")
    # Rough estimate (pages are typically 4KB)
    MEM_TOTAL=$(( (MEM_FREE + MEM_ACTIVE) * 4 / 1024 ))
    echo "${CPU}|${MEM_TOTAL}"
}

display_status() {
    if [[ "$WATCH_MODE" == "true" ]]; then
        clear
    fi
    print_header
    
    # Agent Status
    echo -e "${BOLD}${BLUE}📊 Trading Agent Status${NC}"
    echo -e "  Status: $(check_agent_running)"
    echo ""
    
    # Portfolio Information
    PORTFOLIO_VALUE=$(get_portfolio_value)
    POSITION_COUNT=$(get_positions)
    echo -e "${BOLD}${BLUE}💰 Portfolio${NC}"
    echo -e "  Value: ${GREEN}\$${PORTFOLIO_VALUE}${NC}"
    echo -e "  Active Positions: ${CYAN}${POSITION_COUNT}${NC}"
    echo ""
    
    # Recent Trades
    echo -e "${BOLD}${BLUE}📈 Recent Trades (Last 5)${NC}"
    RECENT_TRADES=$(get_recent_trades)
    if [[ -n "$RECENT_TRADES" ]]; then
        echo "$RECENT_TRADES" | while IFS= read -r line; do
            if [[ "$line" == *"BUY"* ]]; then
                echo -e "  ${GREEN}${line}${NC}"
            elif [[ "$line" == *"SELL"* ]]; then
                echo -e "  ${YELLOW}${line}${NC}"
            else
                echo -e "  ${line}"
            fi
        done
    else
        echo -e "  ${YELLOW}No recent trades${NC}"
    fi
    echo ""
    
    # Circuit Breaker Status
    echo -e "${BOLD}${BLUE}🔌 Circuit Breaker${NC}"
    CB_STATUS=$(get_circuit_breaker_status)
    if [[ -n "$CB_STATUS" ]]; then
        if [[ "$CB_STATUS" == *"CLOSED"* ]]; then
            echo -e "  ${GREEN}${CB_STATUS}${NC}"
        else
            echo -e "  ${YELLOW}${CB_STATUS}${NC}"
        fi
    else
        echo -e "  ${CYAN}Status not available${NC}"
    fi
    echo ""
    
    # Recent Errors/Warnings
    echo -e "${BOLD}${BLUE}⚠️  Recent Issues (Last 5)${NC}"
    ERRORS=$(get_recent_errors | head -5)
    if [[ -n "$ERRORS" ]]; then
        echo "$ERRORS" | while IFS= read -r line; do
            if [[ "$line" == *"ERROR"* ]]; then
                echo -e "  ${RED}${line}${NC}"
            elif [[ "$line" == *"BLOCKED"* ]]; then
                echo -e "  ${YELLOW}${line}${NC}"
            else
                echo -e "  ${line}"
            fi
        done
    else
        echo -e "  ${GREEN}No recent errors${NC}"
    fi
    echo ""
    
    # System Health
    HEALTH=$(get_system_health)
    CPU=$(echo "$HEALTH" | cut -d'|' -f1)
    MEM=$(echo "$HEALTH" | cut -d'|' -f2)
    echo -e "${BOLD}${BLUE}💻 System Health${NC}"
    echo -e "  CPU Usage: ${CYAN}${CPU}%${NC}"
    echo -e "  Memory: ${CYAN}${MEM} MB${NC}"
    echo ""
    
    # Quick Actions
    echo -e "${BOLD}${MAGENTA}⚡ Quick Actions${NC}"
    echo -e "  Press ${BOLD}Ctrl+C${NC} to exit"
    if [[ "$WATCH_MODE" == "true" ]]; then
        echo -e "  Auto-refreshing every ${CYAN}${REFRESH_INTERVAL}s${NC}"
    fi
    echo ""
}

# Main execution
if [[ "$WATCH_MODE" == "true" ]]; then
    while true; do
        display_status
        sleep "$REFRESH_INTERVAL"
    done
else
    display_status
fi

