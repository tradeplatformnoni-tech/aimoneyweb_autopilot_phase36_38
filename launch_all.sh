#!/usr/bin/env bash
# 🌍 NeoLight FullStack Autostart (24/7 Background Launcher)
# Ensures all services run in background with logs and health lock protection.

set -Eeuo pipefail
cd ~/neolight || exit 1

# Load environment variables (API keys, feature flags) once for all child processes
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

LOCKFILE="/tmp/neolight_launcher.lock"
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "[⚠️] Another launcher already running — aborting."
  exit 0
fi

launch() {
  local name="$1"; shift
  local cmd="$*"
  echo "[🚀] Launching $name ..."
  nohup bash -c "$cmd" >> "${LOG_DIR}/${name}.log" 2>&1 &
  sleep 0.5
}

echo "[🌐] Starting NeoLight Autopilot stack @ $(date '+%F %T')"

# ───── Guardian + Dashboard ─────
launch "dashboard_live" "bash phases/phase_41_50_atlas_dashboard.sh"
launch "guardian_live"  "python3 agents/guardian_agent.py"

# ───── Core AI Intelligence Phases ─────
launch "risk_governor_live" "bash phases/phase_101_120_risk_governor.sh"
launch "drawdown_guard_live" "bash phases/phase_121_130_drawdown_guard.sh"
launch "allocator_live" "python3 phases/phase_131_140_allocator.py"
launch "neural_tuner_live" "python3 phases/phase_91_100_neural_tuner.py"

# ───── Trader + Sentiment + Sync ─────
launch "trader_bridge" "python3 trader/smart_trader.py"
launch "atlas_feedback_live" "bash phases/phase_81_90_atlas_feedback.sh"
launch "drive_sync_bg" "bash scripts/rclone_sync.sh"
launch "sports_betting" "python3 agents/sports_betting_agent.py"

echo "[✅] All background processes launched. Logs are in ~/neolight/logs/"
flock -u 9
 
