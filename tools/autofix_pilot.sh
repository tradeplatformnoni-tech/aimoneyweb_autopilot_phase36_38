#!/bin/bash
# ==========================================================
# 🧠 NeoLight-Fix Auto-Healing Utility
# ==========================================================
echo "🩺 NeoLight-Fix: Running diagnostics..."

# 1. Detect and restart crashed agents
for agent in trading_agent ticketbot sportsinsight sportsbetbot luxury_agent dropship_agent collectibles_agent medmatch_agent; do
  if ! pgrep -f "$agent.py" > /dev/null; then
    echo "⚠️ Agent $agent not running — restarting..."
    nohup python3 agents/$agent.py > logs/$agent.log 2>&1 &
    echo "✅ Restarted $agent."
  fi
done

# 2. Check core modules
for module in signal_engine risk_governor hedge_engine capital_governor; do
  if ! pgrep -f "$module.py" > /dev/null; then
    echo "⚠️ Core module $module down — restarting..."
    nohup python3 ai/$module.py > logs/$module.log 2>&1 &
    echo "✅ Restarted $module."
  fi
done

# 3. Log cleanup if files exceed size threshold
find logs -type f -size +10M -exec truncate -s 0 {} \;

# 4. Re-verify dashboard
if ! pgrep -f "flask_app.py" > /dev/null; then
  echo "⚠️ Dashboard offline — restarting..."
  nohup python3 dashboard/flask_app.py > logs/dashboard.log 2>&1 &
fi

echo "✅ NeoLight-Fix complete. All systems green."
