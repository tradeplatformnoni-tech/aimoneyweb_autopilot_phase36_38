#!/usr/bin/env python3
"""
Revenue Monitor - Phase 1300-1500
Monitors profitability of all revenue agents and auto-pauses unprofitable ones
Stores outputs in state/revenue_by_agent.json
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

REVENUE_FILE = STATE / "revenue_by_agent.json"
AGENT_PROFIT_THRESHOLD = float(os.getenv("NEOLIGHT_PROFIT_THRESHOLD", "-0.05"))  # -5% threshold


def load_revenue_data() -> dict[str, Any]:
    """Load current revenue tracking data."""
    if REVENUE_FILE.exists():
        try:
            return json.loads(REVENUE_FILE.read_text())
        except:
            pass
    return {"agents": {}, "last_update": None, "paused_agents": []}


def save_revenue_data(data: dict[str, Any]) -> None:
    """Save revenue tracking data."""
    data["last_update"] = datetime.now(UTC).isoformat()
    REVENUE_FILE.write_text(json.dumps(data, indent=2))


def check_agent_profitability(agent_name: str, revenue_data: dict[str, Any]) -> bool:
    """Check if agent is profitable based on its revenue data."""
    agent_info = revenue_data.get("agents", {}).get(agent_name, {})

    # Check various profit metrics
    pnl_pct = agent_info.get("pnl_pct", 0.0)
    total_revenue = agent_info.get("total_revenue", 0.0)
    total_cost = agent_info.get("total_cost", 0.0)

    # Calculate net profit percentage
    if total_cost > 0:
        net_profit_pct = (total_revenue - total_cost) / total_cost
    else:
        net_profit_pct = pnl_pct if pnl_pct else 0.0

    # Agent is profitable if above threshold
    return net_profit_pct > AGENT_PROFIT_THRESHOLD


def update_agent_revenue(
    agent_name: str, revenue: float, cost: float = 0.0, metadata: dict | None = None
) -> None:
    """Update revenue tracking for a specific agent."""
    data = load_revenue_data()

    if "agents" not in data:
        data["agents"] = {}

    if agent_name not in data["agents"]:
        data["agents"][agent_name] = {
            "total_revenue": 0.0,
            "total_cost": 0.0,
            "transaction_count": 0,
            "last_transaction": None,
            "status": "active",
        }

    agent = data["agents"][agent_name]
    agent["total_revenue"] = agent.get("total_revenue", 0.0) + revenue
    agent["total_cost"] = agent.get("total_cost", 0.0) + cost
    agent["transaction_count"] = agent.get("transaction_count", 0) + 1
    agent["last_transaction"] = datetime.now(UTC).isoformat()

    if metadata:
        agent.update(metadata)

    # Calculate PnL percentage
    if agent["total_cost"] > 0:
        agent["pnl_pct"] = (agent["total_revenue"] - agent["total_cost"]) / agent["total_cost"]
    else:
        agent["pnl_pct"] = 0.0

    # Check profitability and update status
    if not check_agent_profitability(agent_name, data):
        agent["status"] = "paused"
        if agent_name not in data.get("paused_agents", []):
            data.setdefault("paused_agents", []).append(agent_name)
            print(
                f"[revenue_monitor] Agent {agent_name} marked as unprofitable (PnL: {agent['pnl_pct']:.2%})",
                flush=True,
            )
    else:
        agent["status"] = "active"
        if agent_name in data.get("paused_agents", []):
            data["paused_agents"].remove(agent_name)

    save_revenue_data(data)


def get_agent_status(agent_name: str) -> dict[str, Any]:
    """Get current status and revenue data for an agent."""
    data = load_revenue_data()
    return data.get("agents", {}).get(agent_name, {"status": "unknown"})


def main():
    """Monitor loop: periodically check agent profitability and log status."""
    print(
        f"[revenue_monitor] Starting revenue monitoring loop @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    while True:
        try:
            data = load_revenue_data()

            # Log summary
            active_count = len(
                [a for a in data.get("agents", {}).values() if a.get("status") == "active"]
            )
            paused_count = len(data.get("paused_agents", []))
            total_revenue = sum(
                a.get("total_revenue", 0.0) for a in data.get("agents", {}).values()
            )

            print(
                f"[revenue_monitor] Active: {active_count}, Paused: {paused_count}, Total Revenue: ${total_revenue:.2f}",
                flush=True,
            )

            time.sleep(300)  # Check every 5 minutes

        except KeyboardInterrupt:
            print("[revenue_monitor] Shutting down gracefully...", flush=True)
            break
        except Exception as e:
            print(f"[revenue_monitor] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
