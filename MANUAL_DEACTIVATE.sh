#!/bin/bash
# 🛑 Manual Failover Deactivation Script
# Deactivates all apps (scales back to 0)

set -e

echo "🛑 Manual Failover Deactivation"
echo "=============================="
echo ""
echo "This will deactivate all 7 apps (scales to 0):"
echo ""

read -p "Deactivate all apps now? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🛑 Deactivating apps..."

APPS="neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk"
SUCCESS=0

for app in $APPS; do
    echo -n "  Deactivating $app... "
    if flyctl scale count app=0 --app "$app" --yes >/dev/null 2>&1; then
        echo "✅"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "⚠️"
    fi
    sleep 1
done

echo ""
echo "✅ Deactivation complete!"
echo "   $SUCCESS/7 apps deactivated"
echo ""
echo "All apps are now in standby mode (no cost)"
