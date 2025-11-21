#!/usr/bin/env python3
"""
Chaos Controller - Controlled Failure Injection
================================================
Injects controlled failures to test system resilience.

Features:
- Controlled failure injection
- Test scenarios: network latency, resource exhaustion, agent crashes
- Verify recovery mechanisms
- Measure recovery time objectives (RTO)
"""

import json
import os
import signal
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

CHAOS_STATE_FILE = STATE / "chaos_state.json"
CHAOS_RESULTS_FILE = STATE / "chaos_results.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
CHAOS_ENABLED = os.getenv("CHAOS_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram(message: str) -> None:
    """Send Telegram alert."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


class ChaosController:
    """Chaos engineering controller."""

    def __init__(self):
        self.state = self.load_state()
        self.results = []

    def load_state(self) -> dict[str, Any]:
        """Load chaos state."""
        if CHAOS_STATE_FILE.exists():
            try:
                return json.loads(CHAOS_STATE_FILE.read_text())
            except Exception:
                return {"enabled": False, "scenarios": []}
        return {"enabled": False, "scenarios": []}

    def save_state(self) -> None:
        """Save chaos state."""
        try:
            CHAOS_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    def inject_agent_crash(self, agent_name: str) -> dict[str, Any]:
        """Inject agent crash (kill process)."""
        if not CHAOS_ENABLED:
            return {"status": "disabled", "message": "Chaos engineering disabled"}

        start_time = time.time()

        try:
            # Find and kill agent process
            result = subprocess.run(
                ["pgrep", "-f", f"{agent_name}.py"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except Exception:
                        pass

                # Measure recovery time
                recovery_time = self._measure_recovery_time(agent_name, start_time)

                result_data = {
                    "scenario": "agent_crash",
                    "agent": agent_name,
                    "injection_time": datetime.now(UTC).isoformat(),
                    "recovery_time_seconds": recovery_time,
                    "success": recovery_time < 60,  # Recovery within 60s
                }

                self.results.append(result_data)
                self._save_results()

                return result_data
            else:
                return {"status": "error", "message": f"Agent {agent_name} not running"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def inject_network_latency(self, agent_name: str, latency_ms: int = 100) -> dict[str, Any]:
        """Inject network latency (simulated)."""
        if not CHAOS_ENABLED:
            return {"status": "disabled", "message": "Chaos engineering disabled"}

        # In a real implementation, this would use tc (traffic control) on Linux
        # For now, we'll just log it
        result_data = {
            "scenario": "network_latency",
            "agent": agent_name,
            "latency_ms": latency_ms,
            "injection_time": datetime.now(UTC).isoformat(),
            "status": "simulated",
        }

        self.results.append(result_data)
        self._save_results()

        return result_data

    def inject_resource_exhaustion(self, agent_name: str, resource_type: str = "memory") -> dict[str, Any]:
        """Inject resource exhaustion (simulated)."""
        if not CHAOS_ENABLED:
            return {"status": "disabled", "message": "Chaos engineering disabled"}

        result_data = {
            "scenario": "resource_exhaustion",
            "agent": agent_name,
            "resource_type": resource_type,
            "injection_time": datetime.now(UTC).isoformat(),
            "status": "simulated",
        }

        self.results.append(result_data)
        self._save_results()

        return result_data

    def _measure_recovery_time(self, agent_name: str, start_time: float, max_wait: int = 120) -> float:
        """Measure time until agent recovers."""
        elapsed = 0
        check_interval = 5

        while elapsed < max_wait:
            time.sleep(check_interval)
            elapsed += check_interval

            # Check if agent is running
            result = subprocess.run(
                ["pgrep", "-f", f"{agent_name}.py"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return elapsed

        return max_wait  # Timeout

    def _save_results(self) -> None:
        """Save chaos test results."""
        try:
            # Keep only last 1000 results
            if len(self.results) > 1000:
                self.results = self.results[-1000:]

            CHAOS_RESULTS_FILE.write_text(json.dumps(self.results, indent=2))
        except Exception:
            pass

    def run_scenario(self, scenario_name: str, **kwargs) -> dict[str, Any]:
        """Run a chaos scenario."""
        if scenario_name == "agent_crash":
            return self.inject_agent_crash(kwargs.get("agent_name", ""))
        elif scenario_name == "network_latency":
            return self.inject_network_latency(
                kwargs.get("agent_name", ""), kwargs.get("latency_ms", 100)
            )
        elif scenario_name == "resource_exhaustion":
            return self.inject_resource_exhaustion(
                kwargs.get("agent_name", ""), kwargs.get("resource_type", "memory")
            )
        else:
            return {"status": "error", "message": f"Unknown scenario: {scenario_name}"}


def main() -> None:
    """Main chaos controller loop (only runs if enabled)."""
    if not CHAOS_ENABLED:
        print("[chaos_controller] Chaos engineering disabled (set CHAOS_ENABLED=true to enable)", flush=True)
        return

    print(
        f"[chaos_controller] 🎲 Chaos Controller starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    controller = ChaosController()

    # Chaos scenarios run on schedule (e.g., weekly in test environment)
    # This is a placeholder - actual chaos tests should be run via scripts/chaos_test_suite.py
    print("[chaos_controller] Use scripts/chaos_test_suite.py to run chaos tests", flush=True)


if __name__ == "__main__":
    main()

