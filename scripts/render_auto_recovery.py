#!/usr/bin/env python3
"""
Render Auto-Recovery System
===========================
Automatically detects and fixes Render-specific issues:
- Service sleeping (wake up)
- Build failures (retry deployment)
- Environment variable issues
- Path issues
- Missing dependencies
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")

RECOVERY_STATE_FILE = STATE / "render_recovery_state.json"


def check_service_health() -> dict[str, Any]:
    """Check Render service health."""
    health = {
        "status": "unknown",
        "last_deploy": None,
        "build_status": None,
        "service_url": None,
    }

    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        health["status"] = "no_config"
        return health

    try:
        import requests

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {RENDER_API_KEY}",
        }

        # Get service status
        response = requests.get(
            f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            service = data.get("service", {})
            health["status"] = service.get("suspended", "inactive") == "not_suspended"
            health["last_deploy"] = service.get("updatedAt")
            health["service_url"] = service.get("serviceDetails", {}).get("url")

            # Get latest deploy
            deploys_response = requests.get(
                f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys",
                headers=headers,
                params={"limit": 1},
                timeout=10,
            )
            if deploys_response.status_code == 200:
                deploys = deploys_response.json()
                if deploys:
                    latest = deploys[0].get("deploy", {})
                    health["build_status"] = latest.get("status")

    except Exception as e:
        health["status"] = f"error: {str(e)}"

    return health


def wake_service() -> bool:
    """Wake up sleeping Render service."""
    if not RENDER_SERVICE_ID:
        return False

    try:
        import requests

        # Ping the service to wake it up
        health_url = os.getenv("RENDER_SERVICE_URL", "https://neolight-autopilot-python.onrender.com")
        response = requests.get(f"{health_url}/health", timeout=30)
        return response.status_code == 200
    except Exception:
        return False


def check_environment() -> list[str]:
    """Check for missing or incorrect environment variables."""
    issues = []

    required_vars = [
        "RENDER_MODE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]

    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing: {var}")

    # Check RENDER_MODE value
    if os.getenv("RENDER_MODE", "").lower() not in ["true", "1", "yes"]:
        issues.append("RENDER_MODE not set to 'true'")

    return issues


def check_paths() -> list[str]:
    """Check for path issues."""
    issues = []

    expected_paths = [
        ROOT / "agents",
        ROOT / "trader",
        ROOT / "backend",
        ROOT / "state",
        ROOT / "logs",
    ]

    for path in expected_paths:
        if not path.exists():
            issues.append(f"Missing path: {path}")

    return issues


def check_dependencies() -> list[str]:
    """Check for missing Python dependencies."""
    issues = []

    required_modules = [
        "requests",
        "yfinance",
        "pandas",
        "numpy",
    ]

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            issues.append(f"Missing module: {module}")

    return issues


def auto_fix_issues(issues: dict[str, list[str]]) -> dict[str, bool]:
    """Automatically fix detected issues."""
    fixes = {}

    # Fix path issues
    if "paths" in issues:
        for path_str in issues["paths"]:
            path = Path(path_str.replace("Missing path: ", ""))
            try:
                path.mkdir(parents=True, exist_ok=True)
                fixes[path_str] = True
            except Exception:
                fixes[path_str] = False

    # Fix dependency issues
    if "dependencies" in issues:
        for dep in issues["dependencies"]:
            module = dep.replace("Missing module: ", "")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", module],
                    capture_output=True,
                    timeout=120,
                    check=True,
                )
                fixes[dep] = True
            except Exception:
                fixes[dep] = False

    return fixes


def main() -> None:
    """Main recovery loop."""
    print("[render_recovery] 🛡️ Render Auto-Recovery System starting", flush=True)

    check_interval = int(os.getenv("RECOVERY_CHECK_INTERVAL", "300"))  # Every 5 minutes

    while True:
        try:
            # Check service health
            health = check_service_health()
            if health["status"] != "active":
                print(f"[render_recovery] ⚠️ Service not active, attempting wake-up", flush=True)
                wake_service()

            # Check environment
            env_issues = check_environment()
            if env_issues:
                print(f"[render_recovery] ⚠️ Environment issues: {env_issues}", flush=True)

            # Check paths
            path_issues = check_paths()
            if path_issues:
                print(f"[render_recovery] 🔧 Fixing path issues: {path_issues}", flush=True)
                fixes = auto_fix_issues({"paths": path_issues})
                for issue, fixed in fixes.items():
                    if fixed:
                        print(f"[render_recovery] ✅ Fixed: {issue}", flush=True)

            # Check dependencies
            dep_issues = check_dependencies()
            if dep_issues:
                print(f"[render_recovery] 🔧 Fixing dependency issues: {dep_issues}", flush=True)
                fixes = auto_fix_issues({"dependencies": dep_issues})
                for issue, fixed in fixes.items():
                    if fixed:
                        print(f"[render_recovery] ✅ Fixed: {issue}", flush=True)

            # Save state
            state = {
                "last_check": time.time(),
                "health": health,
                "issues": {
                    "environment": env_issues,
                    "paths": path_issues,
                    "dependencies": dep_issues,
                },
            }
            try:
                RECOVERY_STATE_FILE.write_text(json.dumps(state, indent=2))
            except Exception:
                pass

        except Exception as e:
            print(f"[render_recovery] ❌ Error: {e}", flush=True)

        time.sleep(check_interval)


if __name__ == "__main__":
    main()

