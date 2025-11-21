#!/usr/bin/env bash
# NeoLight Fly.io Full Deployment Script
# ======================================
# Complete deployment to Fly.io cloud for 24/7 operation
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

green "🚀 NeoLight Fly.io Full Deployment"
echo ""

# Check flyctl
if ! command -v flyctl >/dev/null 2>&1; then
    yellow "Installing flyctl..."
    curl -L https://fly.io/install.sh | sh
    export PATH="$HOME/.fly/bin:$PATH"
fi

# Check authentication
if ! flyctl auth whoami >/dev/null 2>&1; then
    yellow "Please authenticate with Fly.io:"
    flyctl auth login
fi

# Create app if it doesn't exist
green "📦 Creating Fly.io app..."
flyctl apps create neolight-cloud 2>/dev/null || yellow "App already exists"

# Create persistent volumes
green "💾 Creating persistent volumes..."
flyctl volumes create neolight_state --region iad --size 10 2>/dev/null || yellow "Volume neolight_state already exists"
flyctl volumes create neolight_runtime --region iad --size 5 2>/dev/null || yellow "Volume neolight_runtime already exists"
flyctl volumes create neolight_logs --region iad --size 5 2>/dev/null || yellow "Volume neolight_logs already exists"

# Deploy
green "🚀 Deploying to Fly.io..."
flyctl deploy --app neolight-cloud --config fly.toml

# Set secrets (if .env file exists)
if [ -f "$ROOT_DIR/.env" ]; then
    green "🔐 Setting secrets from .env file..."
    # Read .env file and set secrets (skip comments and empty lines)
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        # Extract key=value pairs
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            # Remove quotes if present
            value="${value#\"}"
            value="${value%\"}"
            value="${value#\'}"
            value="${value%\'}"
            cyan "  Setting $key..."
            flyctl secrets set "${key}=${value}" --app neolight-cloud 2>/dev/null || yellow "  Failed to set $key"
        fi
    done < "$ROOT_DIR/.env"
fi

green "✅ Deployment complete!"
echo ""
cyan "📋 Next steps:"
echo "   1. Check status: flyctl status --app neolight-cloud"
echo "   2. View logs: flyctl logs --app neolight-cloud"
echo "   3. SSH into instance: flyctl ssh console --app neolight-cloud"
echo "   4. Open dashboard: https://neolight-cloud.fly.dev"
echo ""
yellow "⚠️  Remember to set all required secrets:"
echo "   flyctl secrets set ALPACA_API_KEY=xxx --app neolight-cloud"
echo "   flyctl secrets set ALPACA_SECRET_KEY=xxx --app neolight-cloud"
echo "   (See FLYIO_DEPLOYMENT_GUIDE.md for full list)"


