#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Render Deployment Script - Free Tier 24/7                        ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/render_deploy.log"

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

info "Render Deployment - Free Tier Setup"
info "====================================="

# Check for Render CLI
if ! command -v render >/dev/null 2>&1; then
    warn "Render CLI not found. Installing..."
    curl -fsSL https://render.com/install.sh | bash || {
        err "Failed to install Render CLI"
        err "Please install manually: https://render.com/docs/cli"
        exit 1
    }
fi

# Check authentication
info "Checking Render authentication..."
if ! render auth whoami >/dev/null 2>&1; then
    warn "Not authenticated with Render. Please login:"
    info "Run: render auth login"
    exit 1
fi

# Deploy using render.yaml
if [[ -f "$ROOT/render.yaml" ]]; then
    info "Deploying to Render using render.yaml..."
    cd "$ROOT"
    render deploy --yes 2>&1 | tee -a "$LOG_FILE" || {
        err "Render deployment failed"
        exit 1
    }
    ok "Render deployment initiated"
else
    warn "render.yaml not found. Please create it first."
    info "See: $ROOT/render.yaml"
    exit 1
fi

info "Deployment complete!"
info "Next steps:"
info "  1. Configure environment variables in Render dashboard"
info "  2. Set up Cloudflare Worker for keep-alive"
info "  3. Start usage monitor: bash scripts/cloud_orchestrator.sh start"


