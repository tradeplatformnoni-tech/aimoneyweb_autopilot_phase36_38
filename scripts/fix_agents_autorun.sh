#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/neolight"
PY="$ROOT/venv/bin/python3"
LOG="$ROOT/logs/agent_repair_$(date +%H%M%S).log"
echo "🧠 NeoLight Agent Repair — starting..." | tee -a "$LOG"

# 1️⃣ Recheck all critical files exist
AGENTS=(
  "$ROOT/agents/intelligence_orchestrator.py"
  "$ROOT/agents/weights_bridge.py"
  "$ROOT/trader/smart_trader.py"
)
for f in "${AGENTS[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "⚠️ Missing: $f" | tee -a "$LOG"
  else
    chmod +x "$f"
    echo "✅ Verified: $f" | tee -a "$LOG"
  fi
done

# 2️⃣ Validate Python path
if [[ ! -x "$PY" ]]; then
  echo "⚠️ Python venv missing — recreating..." | tee -a "$LOG"
  python3 -m venv "$ROOT/venv"
  source "$ROOT/venv/bin/activate"
  pip install -U fastapi uvicorn plotly pandas numpy yfinance gTTS playsound3 dask polars > /dev/null
else
  echo "✅ Python verified: $($PY --version)" | tee -a "$LOG"
fi

# 3️⃣ Check log + scripts directories
mkdir -p "$ROOT/logs" "$ROOT/scripts" "$ROOT/dashboard" "$ROOT/runtime"

# 4️⃣ Manually test-launch each agent once
for agent in "${AGENTS[@]}"; do
  name="$(basename "$agent")"
  echo "▶️ Testing: $name" | tee -a "$LOG"
  if "$PY" "$agent" >> "$LOG" 2>&1; then
    echo "✅ $name ran successfully (manual test)" | tee -a "$LOG"
  else
    echo "❌ $name test failed — check log." | tee -a "$LOG"
  fi
done

echo "🌀 Restarting Guardian..."
pkill -f neo_light_fix.sh || true
nohup bash "$ROOT/neo_light_fix.sh" >> "$ROOT/logs/guardian_stdout.log" 2>&1 & disown
sleep 3
tail -n 20 "$ROOT/logs/guardian_stdout.log"

echo "✅ Agent repair complete. Guardian restarted."
