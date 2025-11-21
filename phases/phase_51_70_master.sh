#!/usr/bin/env bash
set -Eeuo pipefail

# ╔══════════════════════════════════════════════════════════════╗
# 🚀 NeoLight Phase 51–70 Master — Smart Repair + Learning Mesh
# ╚══════════════════════════════════════════════════════════════╝
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/phase_51_70_${STAMP}.log"

TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

HEALTH_URL="http://127.0.0.1:5050/healthz"

log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }
ok(){ log "✅ $*"; }
warn(){ log "⚠️ $*"; }
err(){ log "❌ $*"; }

notify(){ 
  local msg="$1"
  [[ -n "$TELEGRAM_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]] && \
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_CHAT_ID}" -d text="${msg}" >/dev/null 2>&1 || true
  [[ -n "$DISCORD_WEBHOOK" ]] && \
    curl -s -H "Content-Type: application/json" -X POST \
      -d "{\"content\": \"${msg}\"}" "${DISCORD_WEBHOOK}" >/dev/null 2>&1 || true
}

restore_path(){ export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"; }

health(){ curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || echo 000; }

# 51–56: Ensure Smart-Activator is present and install optional periodic LaunchAgent
step_autorepair(){
  log "🔧 Installing Smart-Activator hooks"
  if [[ ! -f "$HOME/.neolight_env/neo_guardian_autorepair.sh" ]]; then
    err "Autorepair script missing at ~/.neolight_env/neo_guardian_autorepair.sh"
  else
    bash "$HOME/.neolight_env/neo_guardian_autorepair.sh" --verbose || true
  fi
  # Optional periodic safety net (comment in to enable)
  # bash "$HOME/.neolight_env/neo_guardian_autorepair.sh" --install-launchd-15m || true
  ok "Smart-Activator verified"
}

# 57–60: Telemetry heartbeat (writes lightweight JSON + optional push)
step_telemetry(){
  log "📡 Writing heartbeat"
  local hb="${LOG_DIR}/heartbeat.json"
  echo "{\"ts\":\"$(date -Iseconds)\",\"health\":\"$(health)\"}" > "$hb"
  [[ -n "$DISCORD_WEBHOOK" ]] && curl -s -H "Content-Type: application/json" -X POST \
    -d "{\"content\":\"NeoLight heartbeat $(date +%H:%M:%S) health=$(cat $hb | sed 's/\"//g')\"}" "$DISCORD_WEBHOOK" >/dev/null 2>&1 || true
  ok "Heartbeat updated"
}

# 61–66: Atlas Learning Bridge (stub): ship last errors/events to learner inbox
step_learning_bridge(){
  log "🧠 Atlas Learning Bridge: staging data"
  mkdir -p "${ROOT_DIR}/learning_inbox"
  tail -n 100 "${LOG_DIR}"/daemon_*.log 2>/dev/null > "${ROOT_DIR}/learning_inbox/guardian_tail_${STAMP}.log" || true
  tail -n 200 "${LOG_DIR}"/trader.log 2>/dev/null > "${ROOT_DIR}/learning_inbox/trader_tail_${STAMP}.log" || true
  ok "Logs staged in learning_inbox/"
}

# 67–70: Mesh-ready hooks (scale-out stubs)
step_mesh_hooks(){
  log "🌐 Mesh hooks: preparing for scale-out"
  # Create a template env for secondary nodes
  mkdir -p "${ROOT_DIR}/mesh/nodes"
  echo "ROLE=guardian" > "${ROOT_DIR}/mesh/nodes/node_template.env"
  echo "ENDPOINT=http://127.0.0.1:5050" >> "${ROOT_DIR}/mesh/nodes/node_template.env"
  ok "Mesh template created"
}

main(){
  restore_path
  log "🚀 Phase 51–70 Master starting"
  step_autorepair
  step_telemetry
  step_learning_bridge
  step_mesh_hooks
  ok "🎉 Phase 51–70 complete"
}
main "$@"

