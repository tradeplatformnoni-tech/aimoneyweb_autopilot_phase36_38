"""
tools/orchestrator.py
Coordinates all active agents, checks health, and triggers repairs.
"""
import subprocess, time, os, json

AGENTS = json.load(open("config/agents.json")) if os.path.exists("config/agents.json") else []
LOG = "logs/orchestrator.log"

def check_services():
    services = ["uvicorn", "strategy_daemon", "telemetry_daemon"]
    running = []
    for s in services:
        if os.system(f"pgrep -f {s} > /dev/null") == 0:
            running.append(s)
    return running

def auto_fix():
    if not os.path.exists("./neolight-fix"):
        return
    os.system("./neolight-fix")

if __name__ == "__main__":
    while True:
        running = check_services()
        msg = f"[Orchestrator] Running: {running}"
        print(msg)
        open(LOG, "a").write(msg + "\n")
        if len(running) < 3:
            print("⚠️ Missing service detected, running AutoFix...")
            auto_fix()
        time.sleep(300)
