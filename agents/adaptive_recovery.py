#!/usr/bin/env python3
"""
Adaptive Recovery - Learning Optimal Recovery Strategies
=========================================================
Learns optimal recovery strategies and adapts based on success rates.

Features:
- Learn optimal recovery strategies
- Adapt based on success rates
- Optimize recovery time
- Minimize false positives
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

RECOVERY_STRATEGIES_FILE = STATE / "recovery_strategies.json"
RECOVERY_PERFORMANCE_FILE = STATE / "recovery_performance.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class AdaptiveRecovery:
    """Adaptive recovery strategy system."""

    def __init__(self):
        self.strategies = self.load_strategies()
        self.performance = self.load_performance()

    def load_strategies(self) -> dict[str, Any]:
        """Load recovery strategies."""
        if RECOVERY_STRATEGIES_FILE.exists():
            try:
                return json.loads(RECOVERY_STRATEGIES_FILE.read_text())
            except Exception:
                return self._default_strategies()
        return self._default_strategies()

    def save_strategies(self) -> None:
        """Save recovery strategies."""
        try:
            RECOVERY_STRATEGIES_FILE.write_text(json.dumps(self.strategies, indent=2))
        except Exception:
            pass

    def load_performance(self) -> dict[str, Any]:
        """Load recovery performance data."""
        if RECOVERY_PERFORMANCE_FILE.exists():
            try:
                return json.loads(RECOVERY_PERFORMANCE_FILE.read_text())
            except Exception:
                return {}
        return {}

    def save_performance(self) -> None:
        """Save recovery performance."""
        try:
            RECOVERY_PERFORMANCE_FILE.write_text(json.dumps(self.performance, indent=2))
        except Exception:
            pass

    def _default_strategies(self) -> dict[str, Any]:
        """Get default recovery strategies."""
        return {
            "restart": {
                "backoff_initial": 2,
                "backoff_max": 60,
                "backoff_multiplier": 2,
                "max_attempts": 5,
                "cooldown_minutes": 5,
            },
            "retry": {
                "max_retries": 3,
                "retry_delay": 5,
                "exponential_backoff": True,
            },
            "circuit_breaker": {
                "failure_threshold": 3,
                "recovery_timeout": 300,
                "half_open_success_threshold": 2,
            },
        }

    def get_optimal_strategy(self, agent_name: str, error_type: str) -> dict[str, Any]:
        """Get optimal recovery strategy for error."""
        # Check performance history
        key = f"{agent_name}_{error_type}"

        if key in self.performance:
            perf = self.performance[key]
            best_strategy = perf.get("best_strategy", "restart")
            return self.strategies.get(best_strategy, self.strategies["restart"])

        # Default strategy
        return self.strategies["restart"]

    def record_recovery_attempt(
        self,
        agent_name: str,
        error_type: str,
        strategy: str,
        success: bool,
        recovery_time: float,
    ) -> None:
        """Record recovery attempt and update performance."""
        key = f"{agent_name}_{error_type}"

        if key not in self.performance:
            self.performance[key] = {
                "strategies": {},
                "total_attempts": 0,
                "successful_attempts": 0,
                "best_strategy": strategy,
                "best_recovery_time": recovery_time,
            }

        perf = self.performance[key]
        perf["total_attempts"] += 1

        if strategy not in perf["strategies"]:
            perf["strategies"][strategy] = {
                "attempts": 0,
                "successes": 0,
                "total_recovery_time": 0.0,
                "avg_recovery_time": 0.0,
                "success_rate": 0.0,
            }

        strategy_perf = perf["strategies"][strategy]
        strategy_perf["attempts"] += 1

        if success:
            perf["successful_attempts"] += 1
            strategy_perf["successes"] += 1
            strategy_perf["total_recovery_time"] += recovery_time
            strategy_perf["avg_recovery_time"] = (
                strategy_perf["total_recovery_time"] / strategy_perf["successes"]
            )
            strategy_perf["success_rate"] = strategy_perf["successes"] / strategy_perf["attempts"]

            # Update best strategy
            if (
                strategy_perf["success_rate"] > perf["strategies"].get(perf["best_strategy"], {}).get("success_rate", 0)
                or (strategy_perf["success_rate"] == perf["strategies"].get(perf["best_strategy"], {}).get("success_rate", 0)
                    and strategy_perf["avg_recovery_time"] < perf.get("best_recovery_time", float("inf")))
            ):
                perf["best_strategy"] = strategy
                perf["best_recovery_time"] = strategy_perf["avg_recovery_time"]

        self.save_performance()

    def optimize_strategies(self) -> dict[str, Any]:
        """Optimize recovery strategies based on performance."""
        optimizations = {}

        for key, perf in self.performance.items():
            if perf["total_attempts"] < 10:
                continue  # Need more data

            best_strategy = perf["best_strategy"]
            best_perf = perf["strategies"].get(best_strategy, {})

            # Optimize strategy parameters
            if best_strategy == "restart":
                strategy = self.strategies["restart"]
                # Adjust backoff based on success rate
                if best_perf.get("success_rate", 0) < 0.7:
                    strategy["backoff_initial"] = min(strategy["backoff_initial"] * 1.5, 10)
                    strategy["cooldown_minutes"] = min(strategy["cooldown_minutes"] * 1.5, 15)

            optimizations[key] = {
                "strategy": best_strategy,
                "optimizations": strategy if best_strategy == "restart" else {},
            }

        return optimizations


def get_optimal_recovery_strategy(agent_name: str, error_type: str) -> dict[str, Any]:
    """Get optimal recovery strategy."""
    adaptive = AdaptiveRecovery()
    return adaptive.get_optimal_strategy(agent_name, error_type)


def record_recovery_result(
    agent_name: str,
    error_type: str,
    strategy: str,
    success: bool,
    recovery_time: float,
) -> None:
    """Record recovery result."""
    adaptive = AdaptiveRecovery()
    adaptive.record_recovery_attempt(agent_name, error_type, strategy, success, recovery_time)


def main() -> None:
    """Main adaptive recovery loop."""
    print(
        f"[adaptive_recovery] 🔄 Adaptive Recovery starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    adaptive = AdaptiveRecovery()

    optimize_interval = int(os.getenv("ADAPTIVE_OPTIMIZE_INTERVAL", "3600"))  # Every hour

    while True:
        try:
            time.sleep(optimize_interval)

            # Optimize strategies
            optimizations = adaptive.optimize_strategies()
            if optimizations:
                print(f"[adaptive_recovery] Optimized {len(optimizations)} strategies", flush=True)
                adaptive.save_strategies()

        except Exception as e:
            print(f"[adaptive_recovery] Error in main loop: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

