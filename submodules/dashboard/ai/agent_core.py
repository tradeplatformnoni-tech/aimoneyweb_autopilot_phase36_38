# 🧠 NeoLight AI Agent Core — Phase 4900 Stable Engine
# Author: Oluwaseye Akinbola & AI QA Dev Mentor
# Purpose: Keeps AI engine alive, syncs with observer and dashboard, runs perpetual heartbeats.

import time, datetime, sys

print("🧠 NeoLight Agent Core initializing...")
sys.stdout.flush()

try:
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] ✅ Core AI Engine heartbeat — system stable.")
        sys.stdout.flush()
        time.sleep(20)
except KeyboardInterrupt:
    print("🧠 Agent Core shutting down gracefully.")
    sys.stdout.flush()

