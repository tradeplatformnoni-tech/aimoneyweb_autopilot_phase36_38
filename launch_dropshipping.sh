#!/bin/bash
# Launch Dropshipping Automation - NeoLight
# Execute this script to start your autonomous dropshipping business

set -e

ROOT="$HOME/neolight"
cd "$ROOT"

echo "============================================================"
echo "🚀 NeoLight Dropshipping Automation Launcher"
echo "============================================================"
echo ""

# Check for AutoDS token
if [ -z "$AUTODS_TOKEN" ] && [ -z "$AUTODS_API_KEY" ]; then
    echo "⚠️  WARNING: AUTODS_TOKEN or AUTODS_API_KEY not set"
    echo ""
    echo "Please set your AutoDS token:"
    echo "  export AUTODS_TOKEN='a2b1c3bf-d143-4516-905f-cf4bcf365dc0'"
    echo ""
    echo "Or add to ~/.neolight_secrets_template:"
    echo "  export AUTODS_TOKEN='your_token_here'"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Load environment variables
if [ -f "$HOME/.neolight_secrets_template" ]; then
    echo "📋 Loading environment variables..."
    source "$HOME/.neolight_secrets_template"
fi

# Set platform preference
export DROPSHIP_PLATFORM="${DROPSHIP_PLATFORM:-ebay}"
export EBAY_USERNAME="${EBAY_USERNAME:-seakin67}"

echo "✅ Platform: $DROPSHIP_PLATFORM"
echo "✅ eBay Username: $EBAY_USERNAME"
echo ""

# Test AutoDS connection
echo "🔗 Testing AutoDS connection..."
python3 -c "
from agents.autods_integration import test_autods_connection
import sys
if not test_autods_connection():
    print('❌ AutoDS connection failed. Please check your token.')
    sys.exit(1)
" || {
    echo "❌ Connection test failed. Please fix and try again."
    exit 1
}

echo ""
echo "✅ AutoDS connection successful!"
echo ""

# Run product research (optional - update monthly trends)
echo "📊 Running product research (monthly trends)..."
python3 agents/ebay_product_researcher.py || echo "⚠️  Product research failed (non-critical)"

echo ""
echo "============================================================"
echo "🤖 Starting Dropshipping Agent..."
echo "============================================================"
echo ""
echo "The agent will:"
echo "  1. Find trending products"
echo "  2. Search suppliers (AliExpress, CJDropshipping, etc.)"
echo "  3. Calculate profit margins"
echo "  4. List on eBay (via AutoDS)"
echo "  5. Auto-fulfill orders when customers buy"
echo "  6. Track revenue and profits"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "============================================================"
echo ""

# Start dropship agent
python3 agents/dropship_agent.py

