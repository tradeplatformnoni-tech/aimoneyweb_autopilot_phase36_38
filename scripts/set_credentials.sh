#!/bin/bash
# Interactive script to set API credentials and run deployment

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔑 API Credentials Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if credentials already exist
if [[ -n "${RENDER_API_KEY:-}" ]]; then
    echo "${CYAN}ℹ️  RENDER_API_KEY already set${NC}"
    read -p "   Use existing? (y/n) [y]: " use_existing
    if [[ "${use_existing:-y}" != "n" ]]; then
        RENDER_KEY="$RENDER_API_KEY"
    else
        read -p "   Enter Render API Key: " RENDER_KEY
    fi
else
    echo "${YELLOW}📋 Render API Key${NC}"
    echo "   Get it from: https://dashboard.render.com/account/api-keys"
    read -p "   Enter Render API Key: " RENDER_KEY
fi

if [[ -z "$RENDER_KEY" ]]; then
    echo "❌ Render API Key is required"
    exit 1
fi

echo ""

if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    echo "${CYAN}ℹ️  CLOUDFLARE_API_TOKEN already set${NC}"
    read -p "   Use existing? (y/n) [y]: " use_existing
    if [[ "${use_existing:-y}" != "n" ]]; then
        CF_TOKEN="$CLOUDFLARE_API_TOKEN"
    else
        read -p "   Enter Cloudflare API Token: " CF_TOKEN
    fi
else
    echo "${YELLOW}📋 Cloudflare API Token${NC}"
    echo "   Get it from: https://dash.cloudflare.com/profile/api-tokens"
    read -p "   Enter Cloudflare API Token: " CF_TOKEN
fi

if [[ -z "$CF_TOKEN" ]]; then
    echo "❌ Cloudflare API Token is required"
    exit 1
fi

echo ""

if [[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    echo "${CYAN}ℹ️  CLOUDFLARE_ACCOUNT_ID already set${NC}"
    read -p "   Use existing? (y/n) [y]: " use_existing
    if [[ "${use_existing:-y}" != "n" ]]; then
        CF_ACCOUNT_ID="$CLOUDFLARE_ACCOUNT_ID"
    else
        read -p "   Enter Cloudflare Account ID: " CF_ACCOUNT_ID
    fi
else
    echo "${YELLOW}📋 Cloudflare Account ID${NC}"
    echo "   Get it from: https://dash.cloudflare.com (right sidebar)"
    read -p "   Enter Cloudflare Account ID: " CF_ACCOUNT_ID
fi

if [[ -z "$CF_ACCOUNT_ID" ]]; then
    echo "❌ Cloudflare Account ID is required"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "💾 Setting credentials..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Export for current session
export RENDER_API_KEY="$RENDER_KEY"
export CLOUDFLARE_API_TOKEN="$CF_TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID"

echo "${GREEN}✅ Credentials set for current session${NC}"

# Ask to save to .zshrc
read -p "💾 Save to ~/.zshrc for future sessions? (y/n) [y]: " save_to_zshrc
if [[ "${save_to_zshrc:-y}" == "y" ]]; then
    # Remove old entries if they exist
    sed -i.bak '/^export RENDER_API_KEY=/d' ~/.zshrc 2>/dev/null || true
    sed -i.bak '/^export CLOUDFLARE_API_TOKEN=/d' ~/.zshrc 2>/dev/null || true
    sed -i.bak '/^export CLOUDFLARE_ACCOUNT_ID=/d' ~/.zshrc 2>/dev/null || true
    
    # Add new entries
    echo "" >> ~/.zshrc
    echo "# NeoLight API Credentials" >> ~/.zshrc
    echo "export RENDER_API_KEY='$RENDER_KEY'" >> ~/.zshrc
    echo "export CLOUDFLARE_API_TOKEN='$CF_TOKEN'" >> ~/.zshrc
    echo "export CLOUDFLARE_ACCOUNT_ID='$CF_ACCOUNT_ID'" >> ~/.zshrc
    
    echo "${GREEN}✅ Credentials saved to ~/.zshrc${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🚀 Ready to deploy!"
echo "═══════════════════════════════════════════════════════════"
echo ""

read -p "Run automated deployment now? (y/n) [y]: " run_deploy
if [[ "${run_deploy:-y}" == "y" ]]; then
    echo ""
    echo "Starting deployment..."
    echo ""
    cd "$ROOT"
    bash scripts/auto_deploy_all.sh
else
    echo ""
    echo "Credentials are set. Run deployment when ready:"
    echo "  bash scripts/auto_deploy_all.sh"
    echo ""
fi


