#!/usr/bin/env bash
# Stop All Local NeoLight Agents
# ================================
# Run this to stop all local agents before deploying to cloud

echo "🛑 Stopping all local NeoLight agents..."
echo ""

# Stop all agent processes
pkill -f neo_light_fix || true
pkill -f guardian || true
pkill -f intelligence_orchestrator || true
pkill -f smart_trader || true
pkill -f sports_analytics || true
pkill -f dropship_agent || true
pkill -f ml_pipeline || true
pkill -f strategy_research || true
pkill -f market_intelligence || true
pkill -f weights_bridge || true
pkill -f dashboard || true
pkill -f uvicorn || true

# Wait a moment
sleep 2

# Verify all stopped
REMAINING=$(ps aux | grep -E "guardian|intelligence|sports|dropship|ml_pipeline|strategy|market|neo_light_fix" | grep -v grep | wc -l | tr -d ' ')

if [ "$REMAINING" -eq "0" ]; then
    echo "✅ All local agents stopped successfully"
else
    echo "⚠️  Some agents may still be running:"
    ps aux | grep -E "guardian|intelligence|sports|dropship|ml_pipeline|strategy|market|neo_light_fix" | grep -v grep
fi

echo ""
echo "☁️  Agents should now run in cloud (Render/Fly.io)"
echo "   Verify: curl https://neolight-autopilot-python.onrender.com/health"

