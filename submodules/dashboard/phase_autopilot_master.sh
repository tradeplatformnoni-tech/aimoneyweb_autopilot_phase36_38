#!/bin/zsh
# ==============================================================
# 🧠 NeoLight A.I. Wealth Mesh — Unified Autopilot Master Script
# ==============================================================
# Handles: Startup, Auto-Fix, Phase Execution, and Dashboard
# ==============================================================

echo "🚀 Launching NeoLight A.I. Autopilot Master..."
sleep 1

# --------------------------------------------------------------
# 1️⃣ Check Directories and Logs
# --------------------------------------------------------------
echo "📁 Verifying directories..."
mkdir -p logs cache runtime config dashboard scripts agents ai/risk ai/capital ai/providers
touch logs/autopilot_master.log runtime/portfolio.json runtime/goal_config.json

# --------------------------------------------------------------
# 2️⃣ Verify Virtual Environment
# --------------------------------------------------------------
if [ -z "$VIRTUAL_ENV" ]; then
  echo "⚠️ Virtual environment not active. Activating..."
  source venv/bin/activate
fi

# --------------------------------------------------------------
# 3️⃣ Quick Dependency Check + Fix
# --------------------------------------------------------------
echo "📦 Checking dependencies..."
deps=("requests" "pandas" "numpy" "pyyaml" "flask" "plotly")
for pkg in "${deps[@]}"; do
  python - <<PY || pip install "$pkg"
import importlib, sys
try:
    sys.exit(0 if importlib.util.find_spec("${pkg}") else 1)
except AttributeError:
    sys.exit(0)
PY
done

# --------------------------------------------------------------
# 4️⃣ Run Auto-Fix Pilot First
# --------------------------------------------------------------
if [ -f "./neolight_autofix_pilot.sh" ]; then
  echo "🩺 Running NeoLight-Fix first..."
  ./neolight_autofix_pilot.sh >> logs/autofix.log 2>&1
else
  echo "⚠️ AutoFix Pilot not found — skipping..."
fi

# --------------------------------------------------------------
# 5️⃣ Run Core Autopilot (Phases 36–44)
# --------------------------------------------------------------
if [ -f "./phase_autopilot_neo.sh" ]; then
  echo "🧩 Starting AI Wealth Autopilot..."
  ./phase_autopilot_neo.sh >> logs/phase_autopilot.log 2>&1
else
  echo "⚠️ phase_autopilot_neo.sh missing — skipping..."
fi

# --------------------------------------------------------------
# 6️⃣ Run Dashboard (auto-detect free port)
# --------------------------------------------------------------
echo "🌍 Launching NeoLight Dashboard..."
DEFAULT_PORT=5050
ALT_PORT=5051

if lsof -i :$DEFAULT_PORT >/dev/null 2>&1; then
  echo "⚠️ Port $DEFAULT_PORT in use — switching to $ALT_PORT"
  PORT=$ALT_PORT
else
  PORT=$DEFAULT_PORT
fi

nohup python3 dashboard/flask_app.py --port $PORT > logs/dashboard.out 2>&1 &
sleep 3
echo "✅ Dashboard running at: http://127.0.0.1:$PORT"

# --------------------------------------------------------------
# 7️⃣ Final Status Check
# --------------------------------------------------------------
echo "🧠 NeoLight Master Autopilot Complete!"
echo "--------------------------------------------------------------"
echo "📊 Logs:       logs/autopilot_master.log"
echo "🪙 Dashboard:  http://127.0.0.1:$PORT"
echo "🩺 AutoFix:    logs/autofix.log"
echo "⚙️ Phases:     logs/phase_autopilot.log"
echo "--------------------------------------------------------------"

