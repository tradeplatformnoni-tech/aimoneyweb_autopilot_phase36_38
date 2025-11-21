#!/bin/bash
# Restart dropshipping agent properly

cd ~/neolight

echo "🛑 Stopping existing agent..."
pkill -f dropship_agent.py 2>/dev/null
sleep 2

echo "📋 Loading environment..."
source ~/.neolight_secrets_template

echo "✅ Environment loaded:"
echo "   AUTODS_TOKEN: ${AUTODS_TOKEN:0:20}..."
echo "   Platform: ${DROPSHIP_PLATFORM:-ebay}"
echo ""

echo "🚀 Starting agent with environment..."
# Export all variables explicitly for background process
export AUTODS_TOKEN
export DROPSHIP_PLATFORM
export EBAY_USERNAME
nohup env AUTODS_TOKEN="$AUTODS_TOKEN" DROPSHIP_PLATFORM="${DROPSHIP_PLATFORM:-ebay}" EBAY_USERNAME="${EBAY_USERNAME:-seakin67}" python3 agents/dropship_agent.py > logs/dropship_agent.log 2>&1 &
sleep 3

echo ""
echo "📊 Agent Status:"
if ps aux | grep -q "[d]ropship_agent.py"; then
    echo "   ✅ Agent is RUNNING"
    ps aux | grep "[d]ropship_agent.py" | grep -v grep | head -1
else
    echo "   ❌ Agent failed to start"
    echo "   Check logs: tail -50 logs/dropship_agent.log"
    exit 1
fi

echo ""
echo "📋 Recent output:"
tail -10 logs/dropship_agent.log | sed 's/^/   /'

echo ""
echo "✅ Agent restarted successfully!"
echo "   Monitor: tail -f logs/dropship_agent.log"
echo "   Status: ./QUICK_STATUS_CHECK.sh"

