#!/bin/bash
# 💰 Fly.io Cost Reduction Script
# Scales down non-critical apps to reduce monthly costs

set -e

echo "💰 Fly.io Cost Reduction"
echo "========================"
echo ""
echo "Current running apps costing money:"
echo "  - neolight-observer: 1 machine (~$1.50/month)"
echo "  - neolight-guardian: 1 machine (~$1.50/month)"
echo "  - ai-money-web: 2 machines (~$6/month) ⚠️ MAIN COST"
echo ""
echo "Total estimated: ~$9/month"
echo ""
read -p "Scale down these apps to save money? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Scaling down apps..."
    
    # Scale down observer (if not critical)
    echo "Scaling neolight-observer to 0..."
    flyctl scale count app=0 --app neolight-observer --yes 2>&1 || echo "⚠️ Could not scale observer"
    
    # Scale down guardian (if not critical)
    echo "Scaling neolight-guardian to 0..."
    flyctl scale count app=0 --app neolight-guardian --yes 2>&1 || echo "⚠️ Could not scale guardian"
    
    # Ask about ai-money-web (more expensive)
    echo ""
    read -p "Scale ai-money-web? Options: [1] to 1 machine, [2] to 0 machines, [n] skip: " -n 1 -r
    echo ""
    if [[ $REPLY == "1" ]]; then
        echo "Scaling ai-money-web to 1 machine..."
        flyctl scale count app=1 --app ai-money-web --yes 2>&1 || echo "⚠️ Could not scale ai-money-web"
    elif [[ $REPLY == "2" ]]; then
        echo "Scaling ai-money-web to 0..."
        flyctl scale count app=0 --app ai-money-web --yes 2>&1 || echo "⚠️ Could not scale ai-money-web"
    fi
    
    echo ""
    echo "✅ Cost reduction complete!"
    echo ""
    echo "Estimated savings:"
    echo "  - observer: ~$1.50/month"
    echo "  - guardian: ~$1.50/month"
    echo "  - ai-money-web (if scaled): ~$3-6/month"
    echo ""
    echo "Total potential savings: ~$3-9/month"
else
    echo "Cancelled."
fi
