#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Automated Deployment Script - All Steps                           ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/auto_deploy_all.log"

mkdir -p "$LOG_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
ok() { log "${GREEN}✅ $*${NC}"; }
warn() { log "${YELLOW}⚠️  $*${NC}"; }
err() { log "${RED}❌ $*${NC}"; }
info() { log "${CYAN}🚀 $*${NC}"; }

info "=========================================="
info "Automated Deployment - All Steps"
info "=========================================="
info ""

# Step 1: Check prerequisites
info "Step 1: Checking prerequisites..."

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    err "Python 3 not found"
    exit 1
fi
ok "Python 3 found"

# Check required packages
info "  Checking Python packages..."
python3 -c "import requests" 2>/dev/null || {
    warn "  Installing requests..."
    pip3 install requests >/dev/null 2>&1 || {
        err "Failed to install requests. Run: pip3 install requests"
        exit 1
    }
}
ok "  Python packages OK"

# Step 2: Check API credentials
info ""
info "Step 2: Checking API credentials..."

MISSING_CREDS=0

# Render API Key
if [[ -z "${RENDER_API_KEY:-}" ]]; then
    warn "RENDER_API_KEY not set"
    MISSING_CREDS=1
else
    ok "RENDER_API_KEY found"
fi

# Cloudflare credentials
if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    warn "CLOUDFLARE_API_TOKEN not set"
    MISSING_CREDS=1
else
    ok "CLOUDFLARE_API_TOKEN found"
fi

if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    warn "CLOUDFLARE_ACCOUNT_ID not set"
    MISSING_CREDS=1
else
    ok "CLOUDFLARE_ACCOUNT_ID found"
fi

if [[ $MISSING_CREDS -eq 1 ]]; then
    info ""
    info "📋 Missing API credentials. Here's how to get them:"
    info ""
    info "Render API Key:"
    info "  1. Go to: https://dashboard.render.com"
    info "  2. Account Settings → API Keys"
    info "  3. Create API Key"
    info "  4. Run: export RENDER_API_KEY='your_key'"
    info ""
    info "Cloudflare API Token:"
    info "  1. Go to: https://dash.cloudflare.com/profile/api-tokens"
    info "  2. Create Token → Edit Cloudflare Workers"
    info "  3. Run: export CLOUDFLARE_API_TOKEN='your_token'"
    info ""
    info "Cloudflare Account ID:"
    info "  1. Go to: https://dash.cloudflare.com"
    info "  2. Right sidebar → Account ID"
    info "  3. Run: export CLOUDFLARE_ACCOUNT_ID='your_account_id'"
    info ""
    read -p "Press Enter to continue after setting credentials, or Ctrl+C to exit..."
fi

# Step 3: Deploy to Render
info ""
info "Step 3: Deploying to Render..."
if [[ -n "${RENDER_API_KEY:-}" ]]; then
    cd "$ROOT"
    python3 scripts/auto_deploy_render.py 2>&1 | tee -a "$LOG_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        ok "Render deployment complete"
        
        # Read service info
        if [[ -f "$ROOT/run/render_service_info.json" ]]; then
            RENDER_SERVICE_ID=$(python3 -c "import json; print(json.load(open('$ROOT/run/render_service_info.json'))['service_id'])" 2>/dev/null || echo "")
            RENDER_SERVICE_URL=$(python3 -c "import json; print(json.load(open('$ROOT/run/render_service_info.json'))['service_url'])" 2>/dev/null || echo "")
            if [[ -n "$RENDER_SERVICE_ID" ]]; then
                export RENDER_SERVICE_ID
                export RENDER_SERVICE_URL
                ok "Service ID: $RENDER_SERVICE_ID"
            fi
        fi
    else
        err "Render deployment failed"
        exit 1
    fi
else
    warn "Skipping Render deployment (no API key)"
fi

# Step 4: Deploy Cloudflare Worker
info ""
info "Step 4: Deploying Cloudflare Worker..."
if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]] && [[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    if [[ -n "${RENDER_SERVICE_URL:-}" ]]; then
        export RENDER_SERVICE_URL
    fi
    cd "$ROOT"
    python3 scripts/auto_deploy_cloudflare.py 2>&1 | tee -a "$LOG_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        ok "Cloudflare Worker deployment complete"
    else
        err "Cloudflare Worker deployment failed"
        exit 1
    fi
else
    warn "Skipping Cloudflare Worker deployment (missing credentials)"
fi

# Step 5: Start Orchestrator
info ""
info "Step 5: Starting Orchestrator..."
if [[ -n "${RENDER_SERVICE_ID:-}" ]] && [[ -n "${RENDER_API_KEY:-}" ]]; then
    cd "$ROOT"
    bash scripts/cloud_orchestrator.sh start 2>&1 | tee -a "$LOG_FILE"
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        ok "Orchestrator started"
    else
        warn "Orchestrator start failed (may need manual start)"
    fi
else
    warn "Skipping orchestrator start (missing Render credentials)"
fi

# Final summary
info ""
info "=========================================="
info "✅ AUTOMATED DEPLOYMENT COMPLETE"
info "=========================================="
info ""
info "📊 Summary:"
if [[ -n "${RENDER_SERVICE_ID:-}" ]]; then
    info "  ✅ Render service deployed (ID: $RENDER_SERVICE_ID)"
else
    info "  ⏳ Render service: Manual deployment needed"
fi
if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    info "  ✅ Cloudflare Worker deployed"
else
    info "  ⏳ Cloudflare Worker: Manual deployment needed"
fi
info ""
info "📋 Next Steps:"
info "  1. Verify services are running"
info "  2. Test endpoints"
info "  3. Check logs: tail -f logs/cloud_orchestrator.log"
info ""
info "📚 Logs saved to: $LOG_FILE"
info ""


