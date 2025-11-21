#!/usr/bin/env bash
# NeoLight Fly.io Complete Deployment Script
# ==========================================
# Handles all 3 steps: State sync (skip if app doesn't exist), Deploy, Secrets
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="${FLY_APP:-neolight-cloud}"

red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

green "🚀 NeoLight Fly.io Complete Deployment"
echo ""

# Step 0: Check/Install flyctl
green "Step 0: Checking prerequisites..."
if ! command -v flyctl >/dev/null 2>&1; then
    yellow "Installing flyctl..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

# Check authentication
if ! flyctl auth whoami >/dev/null 2>&1; then
    yellow "⚠️  Not authenticated with Fly.io"
    yellow "Please run: flyctl auth login"
    yellow "Then run this script again."
    exit 1
fi

green "✅ flyctl installed and authenticated"
echo ""

# Step 1: Sync state to cloud (only if app exists)
green "Step 1: Syncing state to Fly.io..."
APP_EXISTS=$(flyctl apps list 2>/dev/null | grep -q "$APP_NAME" && echo "yes" || echo "no")

if [ "$APP_EXISTS" = "yes" ]; then
    green "App exists, syncing state..."
    # Create archive of state/runtime
    TMP_ARCHIVE="/tmp/neolight_state_$(date +%s).tar.gz"
    if [ -d "$ROOT_DIR/state" ] || [ -d "$ROOT_DIR/runtime" ]; then
        green "Creating archive of state/runtime..."
        tar -czf "$TMP_ARCHIVE" -C "$ROOT_DIR" state/ runtime/ 2>/dev/null || yellow "Some files may be locked (continuing)"
        
        if [ -f "$TMP_ARCHIVE" ]; then
            green "Note: State will be synced after deployment completes"
            yellow "Run this after deployment: bash scripts/flyio_sync_state.sh to"
            rm -f "$TMP_ARCHIVE"
        fi
    else
        yellow "No state/runtime directories found, skipping sync"
    fi
else
    yellow "App doesn't exist yet (first deployment)"
    yellow "State sync will be available after deployment"
fi
echo ""

# Step 2: Create app and deploy
green "Step 2: Creating app and deploying..."

# Create app if it doesn't exist
if [ "$APP_EXISTS" = "no" ]; then
    green "Creating Fly.io app: $APP_NAME..."
    flyctl apps create "$APP_NAME" 2>/dev/null || yellow "App creation may have failed (continuing)"
fi

# Create persistent volumes if they don't exist
green "Creating persistent volumes..."
flyctl volumes create neolight_state --region iad --size 10 --app "$APP_NAME" 2>/dev/null || yellow "Volume neolight_state may already exist"
flyctl volumes create neolight_runtime --region iad --size 5 --app "$APP_NAME" 2>/dev/null || yellow "Volume neolight_runtime may already exist"
flyctl volumes create neolight_logs --region iad --size 5 --app "$APP_NAME" 2>/dev/null || yellow "Volume neolight_logs may already exist"

# Deploy
green "Deploying to Fly.io..."
flyctl deploy --app "$APP_NAME" --config fly.toml || {
    yellow "⚠️  Deployment may have failed. Check logs above."
    exit 1
}

green "✅ Deployment initiated!"
echo ""

# Step 3: Set secrets
green "Step 3: Setting secrets..."

# Check if .env file exists
if [ -f "$ROOT_DIR/.env" ]; then
    green "Found .env file. Importing secrets..."
    flyctl secrets import --app "$APP_NAME" < "$ROOT_DIR/.env" 2>/dev/null && \
        green "✅ Secrets imported from .env file" || \
        yellow "⚠️  Some secrets may need to be set manually"
else
    yellow "No .env file found."
    yellow "Set secrets manually with: bash scripts/flyio_set_secrets.sh"
    yellow "Or create a .env file with your API keys"
fi

echo ""
green "✅ Deployment process complete!"
echo ""
cyan "📋 Next Steps:"
echo "   1. Wait for deployment to finish (check with: flyctl status --app $APP_NAME)"
echo "   2. View logs: flyctl logs --app $APP_NAME --follow"
echo "   3. Check dashboard: https://$APP_NAME.fly.dev"
echo "   4. Set additional secrets if needed: bash scripts/flyio_set_secrets.sh"
echo "   5. Sync state after app is running: bash scripts/flyio_sync_state.sh to"
echo ""

yellow "⚠️  Important:"
echo "   - Make sure all required secrets are set (ALPACA_API_KEY, ALPACA_SECRET_KEY)"
echo "   - State sync can be done after the app is running"
echo "   - Monitor logs to ensure all services start correctly"
echo ""


