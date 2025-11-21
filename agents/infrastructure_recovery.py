#!/usr/bin/env python3
"""
Infrastructure Layer Recovery - Render Service Recovery
========================================================
Handles recovery at the infrastructure layer (Render services, network, resources).

Features:
- Render service recovery
- Network recovery
- Resource recovery
- Auto-scaling triggers
"""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

INFRASTRUCTURE_RECOVERY_STATE_FILE = STATE / "infrastructure_recovery.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")


class InfrastructureRecovery:
    """Infrastructure layer recovery system."""

    def __init__(self):
        self.state = self.load_state()

    def load_state(self) -> dict[str, Any]:
        """Load recovery state."""
        if INFRASTRUCTURE_RECOVERY_STATE_FILE.exists():
            try:
                return json.loads(INFRASTRUCTURE_RECOVERY_STATE_FILE.read_text())
            except Exception:
                return {"recoveries": []}
        return {"recoveries": []}

    def save_state(self) -> None:
        """Save recovery state."""
        try:
            INFRASTRUCTURE_RECOVERY_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    def recover_render_service(self) -> dict[str, Any]:
        """Recover Render service (wake up, restart, etc.)."""
        if not RENDER_API_KEY or not RENDER_SERVICE_ID:
            return {"status": "no_config", "message": "Render API not configured"}

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
                service = response.json().get("service", {})
                suspended = service.get("suspended", "not_suspended") == "suspended"

                if suspended:
                    # Try to unsuspend (if API supports it)
                    # Render API may not have direct unsuspend, so we ping to wake up
                    health_url = os.getenv("RENDER_SERVICE_URL", "https://neolight-autopilot-python.onrender.com")
                    wake_response = requests.get(f"{health_url}/health", timeout=30)
                    return {
                        "status": "woken",
                        "wake_success": wake_response.status_code == 200,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }

                return {
                    "status": "active",
                    "message": "Service is active",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "message": f"API error: {response.status_code}",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def recover_network(self) -> dict[str, Any]:
        """Recover network connectivity."""
        # Test network connectivity
        try:
            import requests

            test_urls = [
                "https://api.render.com",
                "https://api.telegram.org",
                "https://api.alpaca.markets",
            ]

            results = {}
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    results[url] = response.status_code == 200
                except Exception:
                    results[url] = False

            all_ok = all(results.values())

            return {
                "status": "ok" if all_ok else "degraded",
                "connectivity": results,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def recover_resources(self) -> dict[str, Any]:
        """Recover resources (cleanup, optimization)."""
        try:
            import psutil

            # Check current resource usage
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(ROOT))

            # If resources are high, suggest cleanup
            actions = []

            if memory.percent > 85:
                actions.append("memory_cleanup")
            if disk.percent > 90:
                actions.append("disk_cleanup")

            return {
                "status": "ok" if not actions else "cleanup_needed",
                "actions": actions,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


def recover_infrastructure_layer() -> dict[str, Any]:
    """Recover at infrastructure layer."""
    recovery = InfrastructureRecovery()

    results = {
        "render_service": recovery.recover_render_service(),
        "network": recovery.recover_network(),
        "resources": recovery.recover_resources(),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    return results


def main() -> None:
    """Main infrastructure recovery (typically called by self-healing agent)."""
    print(
        f"[infrastructure_recovery] 🏗️ Infrastructure Recovery ready @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )


if __name__ == "__main__":
    main()

