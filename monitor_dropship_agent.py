#!/usr/bin/env python3
"""
Monitor Dropship Agent - Free Monitoring Solution
==================================================
Monitors dropship_agent health using Render API (free tier)
"""

import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

RENDER_URL = os.getenv("RENDER_URL", "https://neolight-autopilot-python.onrender.com")
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")  # Free tier includes API access
RENDER_SERVICE_ID = os.getenv("RENDER_DROPSHIP_SERVICE_ID", "")


def check_dropship_agent_via_api():
    """Check dropship agent status via Render health endpoint (FREE)."""
    try:
        # Use public health endpoint (free, no API key needed)
        response = requests.get(f"{RENDER_URL}/agents", timeout=10)

        if response.status_code == 200:
            data = response.json()
            agents = data.get("agents", {})
            dropship = agents.get("dropship_agent", {})

            status = dropship.get("status", "unknown")
            restarts = dropship.get("restarts", -1)
            pid = dropship.get("pid", None)

            if status == "running" and restarts == 0:
                print(f"✅ dropship_agent: Running (PID: {pid}, Restarts: {restarts})")
                return True
            elif status == "running" and restarts > 0:
                print(f"⚠️  dropship_agent: Running but has {restarts} restarts (PID: {pid})")
                return False
            else:
                print(f"❌ dropship_agent: Status={status}, Restarts={restarts}")
                return False
        else:
            print(f"❌ API returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking dropship agent: {e}")
        return False


def check_dropship_agent_logs():
    """Check Render logs for dropship agent errors (requires Render API key)."""
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        print("⚠️  RENDER_API_KEY not set, skipping log check")
        return True

    try:
        url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/logs"
        headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
        params = {"tail": "100"}  # Last 100 log lines

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            logs = response.json()

            # Check for errors
            errors = [
                log
                for log in logs
                if "exit code 1" in log.get("message", "").lower()
                or "error" in log.get("message", "").lower()
                or "traceback" in log.get("message", "").lower()
            ]

            if errors:
                print(f"⚠️  Found {len(errors)} errors in recent logs")
                for error in errors[-5:]:  # Show last 5 errors
                    print(f"   - {error.get('message', '')[:100]}")
                return False
            else:
                print("✅ No errors found in recent logs")
                return True
        else:
            print(f"⚠️  Could not fetch logs: {response.status_code}")
            return True
    except Exception as e:
        print(f"⚠️  Log check failed: {e}")
        return True


if __name__ == "__main__":
    print("🔍 Checking dropship_agent status...")
    print("")

    # Check via health endpoint
    api_check = check_dropship_agent_via_api()

    # Check logs if API key available
    log_check = check_dropship_agent_logs()

    print("")
    if api_check and log_check:
        print("✅ dropship_agent is healthy!")
        sys.exit(0)
    else:
        print("⚠️  dropship_agent may have issues - check Render logs")
        sys.exit(1)
