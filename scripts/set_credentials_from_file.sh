#!/bin/bash
# Non-interactive credential setup from file

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDS_FILE="$ROOT/.api_credentials"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔑 API Credentials Setup (from file)"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [[ ! -f "$CREDS_FILE" ]]; then
    echo "${YELLOW}⚠️  Credentials file not found: $CREDS_FILE${NC}"
    echo ""
    echo "Creating template file..."
    cat > "$CREDS_FILE" << 'EOF'
# API Credentials for NeoLight Deployment
# Fill in your credentials below (remove the # and replace with your values)

#RENDER_API_KEY='your_render_api_key_here'
#CLOUDFLARE_API_TOKEN='your_cloudflare_token_here'
#CLOUDFLARE_ACCOUNT_ID='your_cloudflare_account_id_here'
EOF
    chmod 600 "$CREDS_FILE"
    echo "${GREEN}✅ Created template: $CREDS_FILE${NC}"
    echo ""
    echo "Please edit the file and add your credentials:"
    echo "  nano $CREDS_FILE"
    echo "  # or"
    echo "  open -e $CREDS_FILE"
    echo ""
    exit 0
fi

# Source the credentials file
source "$CREDS_FILE"

# Check if credentials are set
MISSING=0

if [[ -z "${RENDER_API_KEY:-}" ]] || [[ "$RENDER_API_KEY" == "your_render_api_key_here" ]]; then
    echo "${YELLOW}⚠️  RENDER_API_KEY not set or using placeholder${NC}"
    MISSING=1
else
    echo "${GREEN}✅ RENDER_API_KEY found${NC}"
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]] || [[ "$CLOUDFLARE_API_TOKEN" == "your_cloudflare_token_here" ]]; then
    echo "${YELLOW}⚠️  CLOUDFLARE_API_TOKEN not set or using placeholder${NC}"
    MISSING=1
else
    echo "${GREEN}✅ CLOUDFLARE_API_TOKEN found${NC}"
fi

if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]] || [[ "$CLOUDFLARE_ACCOUNT_ID" == "your_cloudflare_account_id_here" ]]; then
    echo "${YELLOW}⚠️  CLOUDFLARE_ACCOUNT_ID not set or using placeholder${NC}"
    MISSING=1
else
    echo "${GREEN}✅ CLOUDFLARE_ACCOUNT_ID found${NC}"
fi

if [[ $MISSING -eq 1 ]]; then
    echo ""
    echo "${YELLOW}Please edit $CREDS_FILE and add your credentials${NC}"
    exit 1
fi

# Export credentials
export RENDER_API_KEY
export CLOUDFLARE_API_TOKEN
export CLOUDFLARE_ACCOUNT_ID

echo ""
echo "${GREEN}✅ All credentials loaded${NC}"

# Ask to save to .zshrc
echo ""
read -p "💾 Save to ~/.zshrc for future sessions? (y/n) [y]: " save_to_zshrc
if [[ "${save_to_zshrc:-y}" == "y" ]]; then
    # Remove old entries if they exist
    sed -i.bak '/^export RENDER_API_KEY=/d' ~/.zshrc 2>/dev/null || true
    sed -i.bak '/^export CLOUDFLARE_API_TOKEN=/d' ~/.zshrc 2>/dev/null || true
    sed -i.bak '/^export CLOUDFLARE_ACCOUNT_ID=/d' ~/.zshrc 2>/dev/null || true
    
    # Add new entries
    echo "" >> ~/.zshrc
    echo "# NeoLight API Credentials" >> ~/.zshrc
    echo "export RENDER_API_KEY='$RENDER_API_KEY'" >> ~/.zshrc
    echo "export CLOUDFLARE_API_TOKEN='$CLOUDFLARE_API_TOKEN'" >> ~/.zshrc
    echo "export CLOUDFLARE_ACCOUNT_ID='$CLOUDFLARE_ACCOUNT_ID'" >> ~/.zshrc
    
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


