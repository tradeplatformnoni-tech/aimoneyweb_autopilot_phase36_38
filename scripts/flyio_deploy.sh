#!/bin/bash
# NeoLight Fly.io Deployment Script
# ==================================
# Enterprise deployment following Google Drive sync pattern
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

green "🚀 NeoLight Fly.io Deployment"
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

# Deploy (but keep it stopped - only activate on failover)
green "📦 Deploying to Fly.io (standby mode)..."

# Check flyctl version and use appropriate command
if flyctl version | grep -q "v0.3"; then
    # Older version - deploy without --no-start flag
    flyctl deploy --config fly.toml || {
        yellow "Deploy failed, trying without config..."
        flyctl deploy
    }
    
    # Scale to 0 after deployment
    green "Scaling to 0 machines (standby mode)..."
    flyctl scale count app=0 --config fly.toml 2>/dev/null || {
        yellow "Scale command failed, app may need manual scaling"
    }
else
    # Newer version
    flyctl deploy --app neolight-failover --no-start
    flyctl scale count app=0 --app neolight-failover
fi

green "✅ Deployment complete!"
yellow "⚠️  App is in standby mode (scaled to 0)"
yellow "   It will auto-start when local system fails"
echo ""
green "📋 Next steps:"
echo "   1. Start failover monitor: ./scripts/flyio_failover_monitor.sh"
echo "   2. Monitor status: flyctl status --config fly.toml"

