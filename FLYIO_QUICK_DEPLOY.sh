#!/usr/bin/env bash
# NeoLight Fly.io Quick Deploy Script
# ===================================
# One-command deployment to Fly.io cloud
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

green "🚀 NeoLight Fly.io Quick Deployment"
echo ""

# Step 1: Check prerequisites
green "Step 1: Checking prerequisites..."
if ! command -v flyctl >/dev/null 2>&1; then
    yellow "Installing flyctl..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

if ! flyctl auth whoami >/dev/null 2>&1; then
    yellow "Please authenticate with Fly.io:"
    flyctl auth login
fi

# Step 2: Sync state to cloud (before deployment)
green ""
green "Step 2: Syncing state to Fly.io..."
if [ -f "$ROOT_DIR/scripts/flyio_sync_state.sh" ]; then
    bash scripts/flyio_sync_state.sh to || yellow "State sync may have failed (continuing anyway)"
else
    yellow "State sync script not found, skipping..."
fi

# Step 3: Set secrets (if .env exists)
green ""
green "Step 3: Setting secrets..."
if [ -f "$ROOT_DIR/.env" ]; then
    cyan "Found .env file. Set secrets from it? (y/n)"
    read -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        flyctl secrets import --app neolight-cloud < "$ROOT_DIR/.env" 2>/dev/null && \
            green "✅ Secrets loaded from .env" || \
            yellow "⚠️  Some secrets may need to be set manually"
    else
        yellow "Skipping secrets import. Set them manually with:"
        yellow "  bash scripts/flyio_set_secrets.sh"
    fi
else
    yellow "No .env file found. Set secrets manually with:"
    yellow "  bash scripts/flyio_set_secrets.sh"
fi

# Step 4: Deploy
green ""
green "Step 4: Deploying to Fly.io..."
flyctl deploy --app neolight-cloud --config fly.toml

# Step 5: Verify
green ""
green "Step 5: Verifying deployment..."
sleep 5
flyctl status --app neolight-cloud

green ""
green "✅ Deployment complete!"
echo ""
cyan "📋 Quick Commands:"
echo "   View logs:     flyctl logs --app neolight-cloud --follow"
echo "   Check status:  flyctl status --app neolight-cloud"
echo "   SSH access:    flyctl ssh console --app neolight-cloud"
echo "   Open dashboard: https://neolight-cloud.fly.dev"
echo ""
yellow "⚠️  Don't forget to:"
echo "   1. Set all required secrets: bash scripts/flyio_set_secrets.sh"
echo "   2. Verify services are running: flyctl logs --app neolight-cloud"
echo "   3. When returning, sync state back: bash scripts/flyio_sync_state.sh from"


