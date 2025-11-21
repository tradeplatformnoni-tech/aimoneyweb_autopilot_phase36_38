#!/usr/bin/env python3
"""
Predictive Maintenance - Proactive Maintenance Scheduling
==========================================================
Predicts when agents need maintenance before failures occur.

Features:
- Predict optimal restart times
- Predict resource exhaustion
- Schedule proactive maintenance
- Minimize downtime
"""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

MAINTENANCE_SCHEDULE_FILE = STATE / "maintenance_schedule.json"
MAINTENANCE_HISTORY_FILE = STATE / "maintenance_history.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
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


class PredictiveMaintenance:
    """Predictive maintenance scheduler."""

    def __init__(self):
        self.schedule = self.load_schedule()
        self.history = self.load_history()

    def load_schedule(self) -> dict[str, Any]:
        """Load maintenance schedule."""
        if MAINTENANCE_SCHEDULE_FILE.exists():
            try:
                return json.loads(MAINTENANCE_SCHEDULE_FILE.read_text())
            except Exception:
                return {}
        return {}

    def save_schedule(self) -> None:
        """Save maintenance schedule."""
        try:
            MAINTENANCE_SCHEDULE_FILE.write_text(json.dumps(self.schedule, indent=2))
        except Exception:
            pass

    def load_history(self) -> list[dict[str, Any]]:
        """Load maintenance history."""
        if MAINTENANCE_HISTORY_FILE.exists():
            try:
                return json.loads(MAINTENANCE_HISTORY_FILE.read_text())
            except Exception:
                return []
        return []

    def save_history(self) -> None:
        """Save maintenance history."""
        try:
            # Keep only last 1000 entries
            if len(self.history) > 1000:
                self.history = self.history[-1000:]
            MAINTENANCE_HISTORY_FILE.write_text(json.dumps(self.history, indent=2))
        except Exception:
            pass

    def predict_restart_time(self, agent_name: str, agent_data: dict[str, Any]) -> Optional[datetime]:
        """Predict when agent should be restarted."""
        uptime_hours = agent_data.get("uptime_hours", 0.0)
        error_rate = agent_data.get("error_rate", 0.0)
        memory_usage = agent_data.get("memory_usage", 0.0)
        restart_count = agent_data.get("restart_count", 0)

        # Heuristic: restart if:
        # - Uptime > 24 hours AND (error_rate > 0.1 OR memory_usage > 80%)
        # - Uptime > 48 hours (preventive)
        # - Error rate > 0.2 (degraded performance)

        if error_rate > 0.2:
            # High error rate - restart soon
            return datetime.now(UTC) + timedelta(minutes=30)
        elif uptime_hours > 48:
            # Long uptime - schedule preventive restart
            return datetime.now(UTC) + timedelta(hours=1)
        elif uptime_hours > 24 and (error_rate > 0.1 or memory_usage > 80):
            # Moderate issues - schedule restart
            return datetime.now(UTC) + timedelta(hours=6)
        else:
            return None

    def predict_resource_exhaustion(self, agent_name: str, agent_data: dict[str, Any]) -> dict[str, Any]:
        """Predict when resources will be exhausted."""
        memory_usage = agent_data.get("memory_usage", 0.0)
        memory_growth_rate = agent_data.get("memory_growth_rate", 0.0)  # % per hour
        disk_usage = agent_data.get("disk_usage", 0.0)
        disk_growth_rate = agent_data.get("disk_growth_rate", 0.0)  # % per hour

        predictions = {}

        # Predict memory exhaustion
        if memory_growth_rate > 0 and memory_usage < 100:
            hours_to_exhaustion = (100 - memory_usage) / memory_growth_rate
            if 0 < hours_to_exhaustion < 24:
                predictions["memory"] = {
                    "hours_until_exhaustion": hours_to_exhaustion,
                    "exhaustion_time": datetime.now(UTC) + timedelta(hours=hours_to_exhaustion),
                }

        # Predict disk exhaustion
        if disk_growth_rate > 0 and disk_usage < 100:
            hours_to_exhaustion = (100 - disk_usage) / disk_growth_rate
            if 0 < hours_to_exhaustion < 24:
                predictions["disk"] = {
                    "hours_until_exhaustion": hours_to_exhaustion,
                    "exhaustion_time": datetime.now(UTC) + timedelta(hours=hours_to_exhaustion),
                }

        return predictions

    def schedule_maintenance(self, agent_name: str, maintenance_type: str, scheduled_time: datetime, reason: str) -> None:
        """Schedule maintenance for an agent."""
        if agent_name not in self.schedule:
            self.schedule[agent_name] = []

        self.schedule[agent_name].append({
            "type": maintenance_type,  # "restart", "cleanup", "optimize"
            "scheduled_time": scheduled_time.isoformat(),
            "reason": reason,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        })

        # Sort by scheduled time
        self.schedule[agent_name].sort(key=lambda x: x["scheduled_time"])

        self.save_schedule()

        # Alert
        message = (
            f"📅 **Maintenance Scheduled**\n"
            f"Agent: `{agent_name}`\n"
            f"Type: {maintenance_type}\n"
            f"Time: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Reason: {reason}"
        )
        send_telegram(message)

    def check_pending_maintenance(self) -> list[dict[str, Any]]:
        """Check for maintenance that should be performed now."""
        pending = []
        now = datetime.now(UTC)

        for agent_name, maintenance_list in self.schedule.items():
            for maintenance in maintenance_list:
                if maintenance["status"] == "pending":
                    scheduled_time = datetime.fromisoformat(maintenance["scheduled_time"].replace("Z", "+00:00"))
                    if scheduled_time <= now:
                        pending.append({
                            "agent": agent_name,
                            "maintenance": maintenance,
                        })

        return pending

    def record_maintenance(self, agent_name: str, maintenance_type: str, success: bool, notes: str = "") -> None:
        """Record maintenance performed."""
        self.history.append({
            "agent": agent_name,
            "type": maintenance_type,
            "success": success,
            "notes": notes,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        self.save_history()

        # Remove from schedule
        if agent_name in self.schedule:
            self.schedule[agent_name] = [
                m for m in self.schedule[agent_name] if m["status"] != "pending"
            ]
            if not self.schedule[agent_name]:
                del self.schedule[agent_name]
            self.save_schedule()


def analyze_agents_for_maintenance(agent_statuses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Analyze all agents and schedule maintenance if needed."""
    pm = PredictiveMaintenance()
    recommendations = {}

    for agent_name, status in agent_statuses.items():
        # Predict restart time
        restart_time = pm.predict_restart_time(agent_name, status)
        if restart_time:
            pm.schedule_maintenance(
                agent_name,
                "restart",
                restart_time,
                f"Preventive restart (uptime: {status.get('uptime_hours', 0):.1f}h, errors: {status.get('error_rate', 0):.2%})",
            )
            recommendations[agent_name] = {"action": "restart", "time": restart_time.isoformat()}

        # Predict resource exhaustion
        resource_predictions = pm.predict_resource_exhaustion(agent_name, status)
        if resource_predictions:
            for resource, prediction in resource_predictions.items():
                pm.schedule_maintenance(
                    agent_name,
                    "cleanup",
                    prediction["exhaustion_time"],
                    f"{resource.capitalize()} exhaustion predicted in {prediction['hours_until_exhaustion']:.1f}h",
                )
                if agent_name not in recommendations:
                    recommendations[agent_name] = {}
                recommendations[agent_name][resource] = prediction

    return recommendations


def main() -> None:
    """Main predictive maintenance loop."""
    print(
        f"[predictive_maintenance] 🔧 Predictive Maintenance starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    pm = PredictiveMaintenance()

    check_interval = int(os.getenv("MAINTENANCE_CHECK_INTERVAL", "300"))  # Every 5 minutes

    while True:
        try:
            # Check for pending maintenance
            pending = pm.check_pending_maintenance()

            for item in pending:
                agent_name = item["agent"]
                maintenance = item["maintenance"]

                print(
                    f"[predictive_maintenance] ⚠️ Maintenance due for {agent_name}: {maintenance['type']}",
                    flush=True,
                )

                # Alert
                message = (
                    f"🔧 **Maintenance Due**\n"
                    f"Agent: `{agent_name}`\n"
                    f"Type: {maintenance['type']}\n"
                    f"Reason: {maintenance['reason']}"
                )
                send_telegram(message)

                # Mark as notified
                maintenance["status"] = "notified"

            pm.save_schedule()

            time.sleep(check_interval)
        except Exception as e:
            print(f"[predictive_maintenance] Error in main loop: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

