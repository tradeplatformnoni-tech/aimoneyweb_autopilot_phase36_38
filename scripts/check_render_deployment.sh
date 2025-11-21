#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 🔍 Render Deployment Status Checker                              ║
# ║ Checks if multi-agent app is running and endpoints are working    ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

SERVICE_URL="https://neolight-autopilot-python.onrender.com"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; }
step() { echo -e "${CYAN}📋 $1${NC}"; }

echo "═══════════════════════════════════════════════════════════════"
echo "🔍 Checking Render Deployment Status"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check root endpoint
step "1. Checking root endpoint..."
ROOT_RESPONSE=$(curl -s "$SERVICE_URL/" 2>/dev/null || echo "")
if echo "$ROOT_RESPONSE" | grep -q "Multi-Agent" || echo "$ROOT_RESPONSE" | grep -q "agents"; then
    info "Multi-agent app is running!"
    echo "$ROOT_RESPONSE" | python3 -m json.tool 2>/dev/null | head -10 || echo "$ROOT_RESPONSE"
elif echo "$ROOT_RESPONSE" | grep -q "Simplified version"; then
    warn "Still running old simplified app"
    echo "$ROOT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$ROOT_RESPONSE"
else
    warn "Unexpected response: $ROOT_RESPONSE"
fi
echo ""

# Check health endpoint
step "2. Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s "$SERVICE_URL/health" 2>/dev/null || echo "")
if [ -n "$HEALTH_RESPONSE" ]; then
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    err "Health endpoint not responding"
fi
echo ""

# Check agents endpoint
step "3. Checking agents endpoint..."
AGENTS_RESPONSE=$(curl -s "$SERVICE_URL/agents" 2>/dev/null || echo "")
if echo "$AGENTS_RESPONSE" | grep -q "agents"; then
    info "Agents endpoint is working!"
    echo "$AGENTS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$AGENTS_RESPONSE"
elif echo "$AGENTS_RESPONSE" | grep -q "Not Found"; then
    warn "Agents endpoint not found (old app still running)"
else
    warn "Unexpected response: $AGENTS_RESPONSE"
fi
echo ""

# Check dashboard endpoint
step "4. Checking dashboard endpoint..."
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/dashboard" 2>/dev/null || echo "000")
if [ "$DASHBOARD_STATUS" = "200" ]; then
    info "Dashboard endpoint is working! (Status: $DASHBOARD_STATUS)"
elif [ "$DASHBOARD_STATUS" = "404" ]; then
    warn "Dashboard endpoint not found (Status: 404 - old app still running)"
else
    warn "Dashboard endpoint status: $DASHBOARD_STATUS"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════"
if echo "$ROOT_RESPONSE" | grep -q "Multi-Agent" && [ "$DASHBOARD_STATUS" = "200" ]; then
    info "✅ Multi-agent app is fully deployed and working!"
    echo ""
    echo "🌐 Access your dashboard:"
    echo "   $SERVICE_URL/dashboard"
    echo ""
    echo "📊 API Endpoints:"
    echo "   • Agents: $SERVICE_URL/agents"
    echo "   • Trades: $SERVICE_URL/api/trades"
    echo "   • Betting: $SERVICE_URL/api/betting"
    echo "   • Revenue: $SERVICE_URL/api/revenue"
elif echo "$ROOT_RESPONSE" | grep -q "Simplified version" || [ "$DASHBOARD_STATUS" = "404" ]; then
    warn "⚠️  Old app still running - manual redeploy needed"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Go to Render dashboard"
    echo "   2. Click 'Manual Deploy' → 'Deploy latest commit'"
    echo "   3. Wait 5-10 minutes"
    echo "   4. Run this script again: bash scripts/check_render_deployment.sh"
else
    warn "⚠️  Status unclear - check Render dashboard logs"
fi
echo "═══════════════════════════════════════════════════════════════"

