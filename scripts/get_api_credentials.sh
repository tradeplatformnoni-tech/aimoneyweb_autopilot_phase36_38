#!/bin/bash
# Helper script to get API credentials

echo "🔑 Opening credential pages in your browser..."
echo ""

# Open Render API Keys page
echo "📋 Render API Key:"
echo "   Opening: https://dashboard.render.com/account/api-keys"
open "https://dashboard.render.com/account/api-keys" 2>/dev/null || echo "   Please open: https://dashboard.render.com/account/api-keys"

sleep 2

# Open Cloudflare API Tokens page
echo ""
echo "📋 Cloudflare API Token:"
echo "   Opening: https://dash.cloudflare.com/profile/api-tokens"
open "https://dash.cloudflare.com/profile/api-tokens" 2>/dev/null || echo "   Please open: https://dash.cloudflare.com/profile/api-tokens"

sleep 2

# Open Cloudflare Account page
echo ""
echo "📋 Cloudflare Account ID:"
echo "   Opening: https://dash.cloudflare.com"
open "https://dash.cloudflare.com" 2>/dev/null || echo "   Please open: https://dash.cloudflare.com"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📝 Instructions:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "1. RENDER_API_KEY:"
echo "   • Click 'Create API Key'"
echo "   • Name: neolight-monitor"
echo "   • Copy the key (shown only once!)"
echo ""
echo "2. CLOUDFLARE_API_TOKEN:"
echo "   • Click 'Create Token'"
echo "   • Use 'Edit Cloudflare Workers' template"
echo "   • Copy the token"
echo ""
echo "3. CLOUDFLARE_ACCOUNT_ID:"
echo "   • Look at right sidebar"
echo "   • Copy 'Account ID'"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "💻 After getting credentials, run:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "export RENDER_API_KEY='your_render_key_here'"
echo "export CLOUDFLARE_API_TOKEN='your_cloudflare_token_here'"
echo "export CLOUDFLARE_ACCOUNT_ID='your_account_id_here'"
echo ""
echo "# Then run deployment:"
echo "bash scripts/auto_deploy_all.sh"
echo ""


