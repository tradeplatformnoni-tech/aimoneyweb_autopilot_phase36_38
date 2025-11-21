#!/bin/bash
# NeoLight Deployment Monitoring Script
# Monitors deployment status, agent health, and observability endpoints

set -euo pipefail

RENDER_URL="https://neolight-autopilot-python.onrender.com"
TIMEOUT=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 NeoLight Deployment Monitor${NC}"
echo "=================================="
echo ""

# Function to check endpoint
check_endpoint() {
    local endpoint="$1"
    local name="$2"
    local url="${RENDER_URL}${endpoint}"
    
    echo -n "Checking ${name}... "
    
    http_code=$(curl -s -o /tmp/response.json -w "%{http_code}" --max-time ${TIMEOUT} "${url}" || echo "000")
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ OK (${http_code})${NC}"
        if [ -s /tmp/response.json ]; then
            echo "   Response preview:"
            head -5 /tmp/response.json | sed 's/^/   /'
            echo ""
        fi
        return 0
    elif [ "$http_code" = "404" ]; then
        echo -e "${YELLOW}⚠️  404 Not Found${NC}"
        return 1
    elif [ "$http_code" = "000" ]; then
        echo -e "${RED}❌ Timeout/Connection Failed${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠️  HTTP ${http_code}${NC}"
        return 1
    fi
}

# Function to check agent status
check_agents() {
    echo -e "\n${BLUE}📊 Agent Status:${NC}"
    local response=$(curl -s --max-time ${TIMEOUT} "${RENDER_URL}/api/agents" || echo "{}")
    
    # Expected agents
    local agents=(
        "intelligence_orchestrator"
        "ml_pipeline"
        "strategy_research"
        "market_intelligence"
        "smart_trader"
        "sports_analytics"
        "sports_betting"
        "dropship_agent"
    )
    
    local all_ok=true
    
    for agent in "${agents[@]}"; do
        if echo "$response" | grep -q "\"${agent}\"" || echo "$response" | grep -qi "${agent}"; then
            echo -e "  ${GREEN}✅${NC} ${agent}"
        else
            echo -e "  ${YELLOW}⚠️${NC}  ${agent} (not found in response)"
            all_ok=false
        fi
    done
    
    if [ "$all_ok" = true ]; then
        echo -e "\n${GREEN}✅ All agents detected${NC}"
    else
        echo -e "\n${YELLOW}⚠️  Some agents may not be running${NC}"
    fi
}

# Main checks
echo -e "${BLUE}1. Core Health Checks:${NC}"
check_endpoint "/health" "Health Check"
check_endpoint "/agents" "Agents Endpoint"

echo -e "\n${BLUE}2. Observability Endpoints:${NC}"
check_endpoint "/observability/summary" "Observability Summary"
check_endpoint "/observability/agents" "Observability Agents"
check_endpoint "/observability/predictions" "Failure Predictions"
check_endpoint "/observability/anomalies" "Anomaly Detections"
check_endpoint "/observability/metrics" "Metrics"
check_endpoint "/metrics" "Prometheus Metrics"

echo -e "\n${BLUE}3. API Endpoints:${NC}"
check_endpoint "/api/trades" "Trades API"
check_endpoint "/api/betting" "Betting API"
check_endpoint "/api/revenue" "Revenue API"
check_endpoint "/api/sports/predictions" "Sports Predictions"

# Check agents
check_agents

echo -e "\n${BLUE}4. Dropship Agent Status:${NC}"
echo "   📝 Check Render logs for:"
echo "      - Successful startup message"
echo "      - No 'exit code 1' errors"
echo "      - '[dropship_agent] Starting multi-platform dropshipping agent'"
echo "      - No Python syntax errors"
echo ""
echo "   🔗 Render Dashboard: https://dashboard.render.com"
echo "   📋 Look for logs of 'dropship_agent' service"

echo -e "\n${BLUE}5. Deployment Status:${NC}"
echo "   Latest commit: b7cd587d4 (dropship_agent Python 3.9 fixes)"
echo "   Previous commit: 640001ae4 (observability endpoints)"
echo ""
echo "   ⏱️  Deployment typically takes 5-10 minutes"
echo "   ✅ Check Render dashboard for deployment status"

echo -e "\n${BLUE}==================================${NC}"
echo -e "${GREEN}✅ Monitoring complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Check Render logs for dropship_agent startup"
echo "  2. Verify no exit code 1 errors"
echo "  3. Monitor agent status via /api/agents endpoint"
echo "  4. Check observability endpoints once deployment completes"

# Cleanup
rm -f /tmp/response.json

