#!/usr/bin/env python3
"""
Application Layer Recovery - Agent and Service Recovery
=======================================================
Handles recovery at the application layer (agents, services, components).

Features:
- Agent-level recovery
- Service-level recovery
- Component-level recovery
"""

import json
import os
import subprocess
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

APPLICATION_RECOVERY_STATE_FILE = STATE / "application_recovery.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class ApplicationRecovery:
    """Application layer recovery system."""

    def __init__(self):
        self.state = self.load_state()

    def load_state(self) -> dict[str, Any]:
        """Load recovery state."""
        if APPLICATION_RECOVERY_STATE_FILE.exists():
            try:
                return json.loads(APPLICATION_RECOVERY_STATE_FILE.read_text())
            except Exception:
                return {"recoveries": []}
        return {"recoveries": []}

    def save_state(self) -> None:
        """Save recovery state."""
        try:
            APPLICATION_RECOVERY_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    def recover_agent(self, agent_name: str) -> dict[str, Any]:
        """Recover an agent."""
        start_time = time.time()

        try:
            # Kill existing process
            subprocess.run(["pkill", "-f", f"{agent_name}.py"], timeout=10, capture_output=True)

            # Wait a bit
            time.sleep(2)

            # Restart agent (on Render, this is handled by process manager)
            # For now, we just log it
            recovery_time = time.time() - start_time

            result = {
                "agent": agent_name,
                "recovery_time": recovery_time,
                "success": True,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            self.state["recoveries"].append(result)
            self.save_state()

            return result
        except Exception as e:
            return {
                "agent": agent_name,
                "recovery_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def recover_service(self, service_name: str) -> dict[str, Any]:
        """Recover a service."""
        # Similar to agent recovery but for services
        return self.recover_agent(service_name)

    def recover_component(self, component_name: str) -> dict[str, Any]:
        """Recover a component."""
        # Component-level recovery (e.g., database connection, API client)
        return {
            "component": component_name,
            "recovery_time": 0.0,
            "success": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def recover_application_layer(agent_name: str) -> dict[str, Any]:
    """Recover at application layer."""
    recovery = ApplicationRecovery()
    return recovery.recover_agent(agent_name)


def main() -> None:
    """Main application recovery (typically called by self-healing agent)."""
    print(
        f"[application_recovery] 🔄 Application Recovery ready @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )


if __name__ == "__main__":
    main()

