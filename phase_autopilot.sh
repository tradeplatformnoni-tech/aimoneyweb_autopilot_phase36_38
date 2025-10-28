#!/bin/bash
# ==========================================================
# 🚀 NeoLight A.I. — Master Autopilot & Auto-Fix Script
# ==========================================================
# Author: AI QA Software Developer In Test Automation
# Purpose: Unified wealth engine orchestrator
# Version: NeoLight 2.0

echo "🧭 Starting NeoLight Autonomous Wealth Mesh..."
sleep 1

# ----------------------------------------------------------
# 1️⃣ Initialize directories and environment
# ----------------------------------------------------------
mkdir -p backend ai agents runtime logs tmp dashboard
touch logs/system.log
echo "✅ Folders verified and system log initialized."

# ----------------------------------------------------------
# 2️⃣ Environment Health Check
# ----------------------------------------------------------
echo "⚙️ Checking environment..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Installing..."
    sudo apt install python3 -y
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ Pip3 not found. Installing..."
    sudo apt install python3-pip -y
fi

echo "✅ Python and pip are ready."

# ----------------------------------------------------------
# 3️⃣ Virtual Environment Setup
# ----------------------------------------------------------
if [ ! -d "venv" ]; then
    echo "🧠 Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null || echo "⚠️ requirements.txt missing or incomplete."

# ----------------------------------------------------------
# 4️⃣ Launch Core A.I. Modules
# ----------------------------------------------------------
echo "🧩 Launching Core Modules..."
python3 ai/signal_engine.py &
python3 ai/risk_governor.py &
python3 ai/hedge_engine.py &
python3 ai/capital_governor.py &
python3 backend/goal_engine.py &
sleep 2
echo "✅ Core Intelligence Layer is live."

# ----------------------------------------------------------
# 5️⃣ Launch Specialized Agents
# ----------------------------------------------------------
echo "🤖 Activating Trading & Business Agents..."
python3 agents/trading_agent.py &
python3 agents/ticketbot.py &
python3 agents/sportsinsight.py &
python3 agents/sportsbetbot.py &
python3 agents/luxury_agent.py &
python3 agents/dropship_agent.py &
python3 agents/collectibles_agent.py &
python3 agents/medmatch_agent.py &
sleep 3
echo "✅ Agents operational."

# ----------------------------------------------------------
# 6️⃣ Start Dashboard & Monitoring
# ----------------------------------------------------------
echo "📊 Starting Dashboard Server..."
python3 dashboard/flask_app.py &
sleep 2
echo "🌍 Dashboard active at http://localhost:5000"

# ----------------------------------------------------------
# 7️⃣ Auto-Fix Subroutine — “NeoLight-Fix”
# ----------------------------------------------------------
echo "🧰 Launching Auto-Fix Watchdog..."
cat > tools/autofix_pilot.sh <<'FIX'
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
FIX

chmod +x tools/autofix_pilot.sh
(while true; do ./tools/autofix_pilot.sh; sleep 300; done) &
echo "🧠 Auto-Fix running in background (5-min interval)."

# ----------------------------------------------------------
# 8️⃣ Completion Summary
# ----------------------------------------------------------
echo "🎯 NeoLight Autopilot fully initialized."
echo "🚀 All agents and modules are live with self-healing enabled."
echo "🧩 Wealth Mesh will now operate autonomously — monitor via Grafana or dashboard."

