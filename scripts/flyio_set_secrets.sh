#!/usr/bin/env bash
# NeoLight Fly.io Secrets Configuration Script
# ============================================
# Interactive script to set all required secrets in Fly.io
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="${FLY_APP:-neolight-cloud}"

red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

green "🔐 NeoLight Fly.io Secrets Configuration"
echo ""

# Check flyctl
if ! command -v flyctl >/dev/null 2>&1; then
    red "❌ flyctl not found. Install with: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check authentication
if ! flyctl auth whoami >/dev/null 2>&1; then
    yellow "Please authenticate with Fly.io:"
    flyctl auth login
fi

# Function to set secret
set_secret() {
    local key=$1
    local description=$2
    local optional=${3:-false}
    
    echo ""
    cyan "$description"
    if [ "$optional" = "true" ]; then
        echo -n "  Enter $key (optional, press Enter to skip): "
    else
        echo -n "  Enter $key (required): "
    fi
    read -s value
    echo ""
    
    if [ -n "$value" ]; then
        flyctl secrets set "${key}=${value}" --app "$APP_NAME" 2>/dev/null && \
            green "  ✅ $key set successfully" || \
            yellow "  ⚠️  Failed to set $key"
    elif [ "$optional" = "false" ]; then
        yellow "  ⚠️  Skipping required secret $key - you may need to set this later"
    fi
}

# Required secrets
green "📋 Required Secrets:"
set_secret "ALPACA_API_KEY" "Alpaca API Key (for paper trading)"
set_secret "ALPACA_SECRET_KEY" "Alpaca Secret Key (for paper trading)"

# Optional secrets
green ""
green "📋 Optional Secrets (press Enter to skip):"
set_secret "SPORTRADAR_API_KEY" "Sportradar API Key (for sports analytics)" "true"
set_secret "AUTODS_API_KEY" "AutoDS API Key (for dropshipping)" "true"
set_secret "AUTODS_TOKEN" "AutoDS Token (for dropshipping)" "true"
set_secret "EBAY_USERNAME" "eBay Username (for dropshipping)" "true"
set_secret "REDDIT_CLIENT_ID" "Reddit Client ID (for market intelligence)" "true"
set_secret "REDDIT_SECRET" "Reddit Secret (for market intelligence)" "true"
set_secret "NEWS_API_KEY" "NewsAPI Key (for market intelligence)" "true"
set_secret "FRED_API_KEY" "FRED API Key (for economic data)" "true"
set_secret "TWITTER_BEARER_TOKEN" "Twitter Bearer Token (for market intelligence)" "true"
set_secret "TELEGRAM_BOT_TOKEN" "Telegram Bot Token (for alerts)" "true"
set_secret "TELEGRAM_CHAT_ID" "Telegram Chat ID (for alerts)" "true"

# Load from .env file if it exists
if [ -f "$ROOT_DIR/.env" ]; then
    echo ""
    green "📁 Found .env file. Load all secrets from it? (y/n)"
    read -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        green "Loading secrets from .env file..."
        flyctl secrets import --app "$APP_NAME" < "$ROOT_DIR/.env" && \
            green "✅ Secrets loaded from .env file" || \
            yellow "⚠️  Some secrets may have failed to load"
    fi
fi

echo ""
green "✅ Secrets configuration complete!"
echo ""
cyan "📋 Next steps:"
echo "   1. Deploy: bash scripts/flyio_deploy_full.sh"
echo "   2. Check status: flyctl status --app $APP_NAME"
echo "   3. View logs: flyctl logs --app $APP_NAME"


