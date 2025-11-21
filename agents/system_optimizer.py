#!/usr/bin/env python3
"""
System Optimizer - Continuous System Optimization
=================================================
Optimizes resource allocation, agent parameters, and system configuration.

Features:
- Optimize resource allocation
- Tune agent parameters
- Optimize check intervals
- Balance performance vs. resource usage
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

OPTIMIZATION_STATE_FILE = STATE / "system_optimization.json"
OPTIMIZATION_HISTORY_FILE = STATE / "optimization_history.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class SystemOptimizer:
    """System optimization engine."""

    def __init__(self):
        self.state = self.load_state()
        self.history = self.load_history()

    def load_state(self) -> dict[str, Any]:
        """Load optimization state."""
        if OPTIMIZATION_STATE_FILE.exists():
            try:
                return json.loads(OPTIMIZATION_STATE_FILE.read_text())
            except Exception:
                return {"optimizations": {}}
        return {"optimizations": {}}

    def save_state(self) -> None:
        """Save optimization state."""
        try:
            OPTIMIZATION_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    def load_history(self) -> list[dict[str, Any]]:
        """Load optimization history."""
        if OPTIMIZATION_HISTORY_FILE.exists():
            try:
                return json.loads(OPTIMIZATION_HISTORY_FILE.read_text())
            except Exception:
                return []
        return []

    def save_history(self) -> None:
        """Save optimization history."""
        try:
            # Keep only last 1000 entries
            if len(self.history) > 1000:
                self.history = self.history[-1000:]
            OPTIMIZATION_HISTORY_FILE.write_text(json.dumps(self.history, indent=2))
        except Exception:
            pass

    def optimize_check_intervals(self, agent_metrics: dict[str, dict[str, Any]]) -> dict[str, int]:
        """Optimize check intervals based on agent stability."""
        optimized_intervals = {}

        for agent_name, metrics in agent_metrics.items():
            error_rate = metrics.get("error_rate", 0.0)
            stability = 1.0 - error_rate

            # More stable agents can be checked less frequently
            if stability > 0.95:
                interval = 300  # 5 minutes
            elif stability > 0.90:
                interval = 180  # 3 minutes
            elif stability > 0.80:
                interval = 120  # 2 minutes
            else:
                interval = 60  # 1 minute

            optimized_intervals[agent_name] = interval

        return optimized_intervals

    def optimize_resource_allocation(self, resource_usage: dict[str, Any]) -> dict[str, Any]:
        """Optimize resource allocation."""
        cpu_usage = resource_usage.get("cpu", 0.0)
        memory_usage = resource_usage.get("memory", 0.0)

        optimizations = {}

        # If CPU is high, suggest reducing check frequency
        if cpu_usage > 80:
            optimizations["check_interval_multiplier"] = 1.5  # Check less frequently
            optimizations["reason"] = "High CPU usage"

        # If memory is high, suggest cleanup
        if memory_usage > 85:
            optimizations["cleanup_interval"] = 300  # Cleanup every 5 minutes
            optimizations["reason"] = "High memory usage"

        return optimizations

    def optimize_agent_parameters(self, agent_name: str, performance: dict[str, Any]) -> dict[str, Any]:
        """Optimize agent-specific parameters."""
        optimizations = {}

        # Example: optimize retry parameters based on success rate
        success_rate = performance.get("success_rate", 0.5)

        if success_rate < 0.5:
            optimizations["max_retries"] = 5  # Increase retries
            optimizations["retry_delay"] = 10  # Increase delay
        elif success_rate > 0.9:
            optimizations["max_retries"] = 2  # Reduce retries
            optimizations["retry_delay"] = 3  # Reduce delay

        return optimizations

    def apply_optimization(self, optimization_type: str, value: Any) -> bool:
        """Apply optimization (update configuration)."""
        try:
            self.state["optimizations"][optimization_type] = {
                "value": value,
                "applied_at": datetime.now(UTC).isoformat(),
            }
            self.save_state()

            # Record in history
            self.history.append({
                "type": optimization_type,
                "value": value,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            self.save_history()

            return True
        except Exception as e:
            print(f"[system_optimizer] Failed to apply optimization: {e}", flush=True)
            return False


def optimize_system(agent_metrics: dict[str, dict[str, Any]], resource_usage: dict[str, Any]) -> dict[str, Any]:
    """Optimize system based on current metrics."""
    optimizer = SystemOptimizer()

    # Optimize check intervals
    intervals = optimizer.optimize_check_intervals(agent_metrics)

    # Optimize resource allocation
    resource_opts = optimizer.optimize_resource_allocation(resource_usage)

    return {
        "check_intervals": intervals,
        "resource_optimizations": resource_opts,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    """Main system optimizer loop."""
    print(
        f"[system_optimizer] ⚙️ System Optimizer starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    optimizer = SystemOptimizer()

    optimize_interval = int(os.getenv("SYSTEM_OPTIMIZE_INTERVAL", "3600"))  # Every hour

    while True:
        try:
            time.sleep(optimize_interval)

            # This would be called with actual metrics
            # For now, just maintain the optimizer
            print("[system_optimizer] Optimization cycle complete", flush=True)

        except Exception as e:
            print(f"[system_optimizer] Error in main loop: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

