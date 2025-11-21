#!/usr/bin/env python3
"""
Performance Learner - Learn from Successful Operations
=======================================================
Learns from successful operations to identify optimal configurations.

Features:
- Learn from successful operations
- Identify optimal configurations
- Predict performance improvements
- Auto-tune system parameters
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

PERFORMANCE_LEARNING_FILE = STATE / "performance_learning.json"
OPTIMAL_CONFIGS_FILE = STATE / "optimal_configs.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class PerformanceLearner:
    """Performance learning system."""

    def __init__(self):
        self.learning_data = self.load_learning_data()
        self.optimal_configs = self.load_optimal_configs()

    def load_learning_data(self) -> list[dict[str, Any]]:
        """Load performance learning data."""
        if PERFORMANCE_LEARNING_FILE.exists():
            try:
                return json.loads(PERFORMANCE_LEARNING_FILE.read_text())
            except Exception:
                return []
        return []

    def save_learning_data(self) -> None:
        """Save performance learning data."""
        try:
            # Keep only last 10000 samples
            if len(self.learning_data) > 10000:
                self.learning_data = self.learning_data[-10000:]
            PERFORMANCE_LEARNING_FILE.write_text(json.dumps(self.learning_data, indent=2))
        except Exception:
            pass

    def load_optimal_configs(self) -> dict[str, Any]:
        """Load optimal configurations."""
        if OPTIMAL_CONFIGS_FILE.exists():
            try:
                return json.loads(OPTIMAL_CONFIGS_FILE.read_text())
            except Exception:
                return {}
        return {}

    def save_optimal_configs(self) -> None:
        """Save optimal configurations."""
        try:
            OPTIMAL_CONFIGS_FILE.write_text(json.dumps(self.optimal_configs, indent=2))
        except Exception:
            pass

    def record_successful_operation(
        self,
        agent_name: str,
        operation: str,
        config: dict[str, Any],
        performance: dict[str, Any],
    ) -> None:
        """Record successful operation for learning."""
        self.learning_data.append({
            "agent": agent_name,
            "operation": operation,
            "config": config,
            "performance": performance,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": True,
        })

        # Update optimal config if this is better
        key = f"{agent_name}_{operation}"

        if key not in self.optimal_configs:
            self.optimal_configs[key] = {
                "config": config,
                "performance": performance,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            current_perf = self.optimal_configs[key]["performance"]
            # Compare performance (e.g., by success rate, speed, etc.)
            if performance.get("success_rate", 0) > current_perf.get("success_rate", 0):
                self.optimal_configs[key] = {
                    "config": config,
                    "performance": performance,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        self.save_learning_data()
        self.save_optimal_configs()

    def get_optimal_config(self, agent_name: str, operation: str) -> Optional[dict[str, Any]]:
        """Get optimal configuration for operation."""
        key = f"{agent_name}_{operation}"
        if key in self.optimal_configs:
            return self.optimal_configs[key]["config"]
        return None

    def predict_performance_improvement(
        self,
        agent_name: str,
        operation: str,
        proposed_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Predict performance improvement from configuration change."""
        # Get current optimal config
        optimal_config = self.get_optimal_config(agent_name, operation)

        if not optimal_config:
            return {"predicted_improvement": 0.0, "confidence": 0.0}

        # Simple heuristic: compare config parameters
        # In a real implementation, this would use ML
        improvement = 0.0
        confidence = 0.5

        # Example: if proposed config has better retry settings
        if (
            proposed_config.get("max_retries", 3) > optimal_config.get("max_retries", 3)
            and optimal_config.get("success_rate", 0.5) < 0.8
        ):
            improvement = 0.1  # 10% improvement predicted
            confidence = 0.6

        return {
            "predicted_improvement": improvement,
            "confidence": confidence,
            "current_config": optimal_config,
            "proposed_config": proposed_config,
        }

    def analyze_performance_trends(self) -> dict[str, Any]:
        """Analyze performance trends and suggest improvements."""
        trends = {}

        # Group by agent and operation
        by_agent_op = {}
        for data in self.learning_data:
            key = f"{data['agent']}_{data['operation']}"
            if key not in by_agent_op:
                by_agent_op[key] = []
            by_agent_op[key].append(data)

        # Analyze trends
        for key, data_list in by_agent_op.items():
            if len(data_list) < 10:
                continue

            # Calculate average performance over time
            recent_perf = [d["performance"].get("success_rate", 0) for d in data_list[-10:]]
            older_perf = [d["performance"].get("success_rate", 0) for d in data_list[-20:-10]]

            if older_perf:
                recent_avg = sum(recent_perf) / len(recent_perf)
                older_avg = sum(older_perf) / len(older_perf)
                trend = recent_avg - older_avg

                trends[key] = {
                    "trend": trend,
                    "recent_avg": recent_avg,
                    "older_avg": older_avg,
                    "improving": trend > 0.05,
                }

        return trends


def record_successful_operation(
    agent_name: str,
    operation: str,
    config: dict[str, Any],
    performance: dict[str, Any],
) -> None:
    """Record successful operation."""
    learner = PerformanceLearner()
    learner.record_successful_operation(agent_name, operation, config, performance)


def get_optimal_config(agent_name: str, operation: str) -> Optional[dict[str, Any]]:
    """Get optimal configuration."""
    learner = PerformanceLearner()
    return learner.get_optimal_config(agent_name, operation)


def main() -> None:
    """Main performance learner loop."""
    print(
        f"[performance_learner] 📈 Performance Learner starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    learner = PerformanceLearner()

    analyze_interval = int(os.getenv("PERFORMANCE_LEARN_INTERVAL", "3600"))  # Every hour

    while True:
        try:
            time.sleep(analyze_interval)

            # Analyze trends
            trends = learner.analyze_performance_trends()
            if trends:
                print(f"[performance_learner] Analyzed {len(trends)} performance trends", flush=True)

        except Exception as e:
            print(f"[performance_learner] Error in main loop: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

