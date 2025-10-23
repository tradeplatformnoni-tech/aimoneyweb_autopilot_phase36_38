#!/bin/bash
# ===========================================================
# 🚀 NeoLight-Fix Pilot — Phase 4950
# Author: Oluwaseye Akinbola & AI QA Mentor
# Purpose: AI-assisted auto-repair and container stability monitor
# ===========================================================

echo ""
echo "🧠 Starting NeoLight-Fix Pilot — Phase 4950"
echo "=========================================================="

# STEP 1 — Environment check
if ! docker info >/dev/null 2>&1; then
  echo "⚠️ Docker not running. Please start Docker Desktop first."
  exit 1
fi

# STEP 2 — Ensure core directories
mkdir -p ai agents dashboard logs runtime config k8s

# STEP 3 — Auto-repair Agent Core
if [ ! -f "ai/agent_core.py" ]; then
  echo "🧩 Restoring Agent Core engine..."
  cat <<'EOF' > ai/agent_core.py
import time, datetime, sys
print("🧠 NeoLight Agent Core (4950) initialized.")
sys.stdout.flush()
try:
  while True:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] ✅ AI Engine heartbeat OK")
    sys.stdout.flush()
    time.sleep(20)
except KeyboardInterrupt:
  print("🧠 Agent Core stopping…")
  sys.stdout.flush()
EOF
fi

# STEP 4 — Monitor containers and auto-heal
echo "🩺 Checking container health..."
mapfile -t containers < < (docker ps --format "{{.Names}}")
for c in "${containers[@]}"; do
  status=$(docker inspect --format='{{.State.Status}}' "$c")
  if [[ "$status" != "running" ]]; then
    echo "⚠️ Container $c is $status — restarting..."
    docker restart "$c" >/dev/null 2>&1 && echo "✅ $c restarted."
  else
    echo "🟢 $c healthy."
  fi
done

# STEP 5 — Auto-diagnose and report
echo "🧭 Running diagnostics..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# STEP 6 — Enable continuous watch mode (optional)
echo "🔁 Watching for future failures (press Ctrl+C to stop)…"
while true; do
  for c in $(docker ps --format "{{.Names}}"); do
    if ! docker inspect --format='{{.State.Running}}' "$c" | grep -q true; then
      echo "🚨 Detected failure in $c — attempting auto-repair..."
      docker restart "$c" >/dev/null 2>&1 && echo "✅ $c restored."
    fi
  done
  sleep 60
done

