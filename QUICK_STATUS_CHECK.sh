#!/bin/bash
# Quick status check script for dropshipping

cd ~/neolight
source ~/.neolight_secrets_template

echo "============================================================"
echo "🚀 DROPSHIPPING STATUS CHECK"
echo "============================================================"
echo ""

# 1. Check agent running
echo "1. Agent Status:"
if ps aux | grep -q "[d]ropship_agent.py"; then
    echo "   ✅ Agent is RUNNING"
    ps aux | grep "[d]ropship_agent.py" | head -1 | awk '{print "   PID: " $2 " | CPU: " $3 "% | Memory: " $4 "%"}'
else
    echo "   ❌ Agent is NOT running"
    echo "   Run: ./launch_dropshipping.sh"
fi
echo ""

# 2. Check AutoDS token
echo "2. AutoDS Token:"
if [ -n "$AUTODS_TOKEN" ]; then
    echo "   ✅ Token configured: ${AUTODS_TOKEN:0:20}..."
elif [ -n "$AUTODS_API_KEY" ]; then
    echo "   ✅ API Key configured: ${AUTODS_API_KEY:0:20}..."
else
    echo "   ❌ No token/API key found"
    echo "   Run: ./setup_autods_token.sh"
fi
echo ""

# 3. Check trending products
echo "3. Trending Products:"
if [ -f "state/trending_products.json" ]; then
    COUNT=$(python3 -c "import json; f=open('state/trending_products.json'); d=json.load(f); print(len(d) if isinstance(d, list) else 1)" 2>/dev/null || echo "1")
    echo "   ✅ Found trending products file ($COUNT items)"
else
    echo "   ⚠️  No trending products file yet"
    echo "   Agent will wait for products to be generated"
fi
echo ""

# 4. Check platform
echo "4. Platform Configuration:"
if [ "$DROPSHIP_PLATFORM" = "ebay" ]; then
    echo "   ✅ Platform: eBay (via AutoDS)"
    echo "   ✅ eBay Username: ${EBAY_USERNAME:-seakin67}"
elif [ "$DROPSHIP_PLATFORM" = "shopify" ]; then
    echo "   ✅ Platform: Shopify"
else
    echo "   ⚠️  Platform: ${DROPSHIP_PLATFORM:-not set}"
fi
echo ""

# 5. Check recent logs
echo "5. Recent Agent Activity:"
if [ -f "logs/dropship_agent.log" ]; then
    echo "   Last 3 lines:"
    tail -3 logs/dropship_agent.log 2>/dev/null | sed 's/^/   /' || echo "   (No recent activity)"
else
    echo "   ⚠️  No log file yet"
fi
echo ""

echo "============================================================"
echo "📋 WHERE TO CHECK FOR PRODUCTS:"
echo "============================================================"
echo ""
echo "1. AutoDS Dashboard:"
echo "   → https://www.autods.com/"
echo "   → Go to 'Products' or 'Listings'"
echo "   → Check active listings count"
echo ""
echo "2. eBay Store:"
echo "   → https://www.ebay.com/mye/myebay/selling"
echo "   → Check 'Active Listings'"
echo "   → Should match AutoDS count"
echo ""
echo "============================================================"
echo "📚 Full guide: HOW_TO_CHECK_IF_IT_WORKS.md"
echo "============================================================"

