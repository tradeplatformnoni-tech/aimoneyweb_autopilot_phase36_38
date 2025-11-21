#!/bin/bash
# Complete Deployment Setup - After Render Service is Live
# Updates Cloudflare Worker, switches to full app, starts orchestrator

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 Complete Deployment Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Load credentials
if [ -f "$ROOT/.api_credentials" ]; then
    source <(grep -v '^#' "$ROOT/.api_credentials" | grep -v '^$' | sed 's/^/export /')
    echo -e "${GREEN}✅ Credentials loaded${NC}"
else
    echo -e "${YELLOW}⚠️  .api_credentials not found${NC}"
    exit 1
fi

# Service details
RENDER_SERVICE_URL="${RENDER_SERVICE_URL:-https://neolight-autopilot-python.onrender.com}"
RENDER_SERVICE_ID="${RENDER_SERVICE_ID:-srv-d4fm045rnu6s73e7ehb0}"

echo -e "${CYAN}Service URL: $RENDER_SERVICE_URL${NC}"
echo -e "${CYAN}Service ID: $RENDER_SERVICE_ID${NC}"
echo ""

# Step 1: Test Render service
echo -e "${CYAN}Step 1: Testing Render service...${NC}"
if curl -s --max-time 10 "$RENDER_SERVICE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Render service is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Render service not responding yet (may still be starting)${NC}"
fi
echo ""

# Step 2: Update Cloudflare Worker
echo -e "${CYAN}Step 2: Updating Cloudflare Worker...${NC}"
export RENDER_SERVICE_URL
if python3 "$ROOT/scripts/auto_deploy_cloudflare.py"; then
    echo -e "${GREEN}✅ Cloudflare Worker updated${NC}"
else
    echo -e "${YELLOW}⚠️  Cloudflare Worker update failed (may need manual update)${NC}"
fi
echo ""

# Step 3: Switch to full app
echo -e "${CYAN}Step 3: Switching to full app...${NC}"
if [ -f "$ROOT/render.yaml" ]; then
    # Update render.yaml to use full app
    sed -i.bak 's/render_app_simple:app/render_app:app/g' "$ROOT/render.yaml"
    git add render.yaml
    git commit -m "Switch to full app with background trader" || echo "No changes to commit"
    git push origin render-deployment
    echo -e "${GREEN}✅ Switched to full app (will auto-deploy)${NC}"
else
    echo -e "${YELLOW}⚠️  render.yaml not found${NC}"
fi
echo ""

# Step 4: Start orchestrator
echo -e "${CYAN}Step 4: Starting orchestrator...${NC}"
export RENDER_SERVICE_ID
if bash "$ROOT/scripts/cloud_orchestrator.sh" start; then
    echo -e "${GREEN}✅ Orchestrator started${NC}"
else
    echo -e "${YELLOW}⚠️  Orchestrator start failed${NC}"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Service URL: $RENDER_SERVICE_URL"
echo "Service ID: $RENDER_SERVICE_ID"
echo ""
echo "Test endpoints:"
echo "  curl $RENDER_SERVICE_URL/health"
echo "  curl https://neolight-keepalive.7bdabfb8a27fd967338fb1865575fa1a.workers.dev/keepalive"
echo ""

