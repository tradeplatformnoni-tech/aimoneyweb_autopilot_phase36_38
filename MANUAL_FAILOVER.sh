#!/bin/bash
# 🚀 Manual Failover Activation Script
# Use this when local system fails - activates all 7 apps on Fly.io

set -e

echo "🚀 Manual Failover Activation"
echo "=============================="
echo ""
echo "This will activate all 7 apps on Fly.io:"
echo "  - neolight-failover"
echo "  - neolight-observer"
echo "  - neolight-guardian"
echo "  - ai-money-web"
echo "  - neolight-atlas"
echo "  - neolight-trade"
echo "  - neolight-risk"
echo ""

read -p "Activate all apps now? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Activating apps..."

APPS="neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk"
SUCCESS=0
FAILED=""

for app in $APPS; do
    echo -n "  Activating $app... "
    if flyctl scale count app=1 --app "$app" --yes >/dev/null 2>&1; then
        echo "✅"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌"
        FAILED="$FAILED $app"
    fi
    sleep 1
done

echo ""
echo "✅ Activation complete!"
echo "   $SUCCESS/7 apps activated"

if [ -n "$FAILED" ]; then
    echo "   ⚠️  Failed: $FAILED"
fi

echo ""
echo "📊 App URLs:"
for app in $APPS; do
    echo "   https://$app.fly.dev/"
done

echo ""
echo "To deactivate later, run: bash MANUAL_DEACTIVATE.sh"
