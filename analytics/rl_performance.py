#!/usr/bin/env python3
"""
NeoLight RL Performance Tracker - Phase 3700-3900
==================================================
Tracks RL model performance, learning curves, strategy weight evolution.
Generates reports comparing RL-weighted strategies vs baseline.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in Python path
_script_dir = Path(__file__).parent.parent.absolute()
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  Install pandas: pip install pandas")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "rl_performance.log"
logger = logging.getLogger("rl_performance")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Performance tracking files
PERFORMANCE_REPORT = STATE / "rl_performance_report.json"
WEIGHT_HISTORY = STATE / "rl_weight_history.json"


class RLPerformanceTracker:
    """
    Tracks RL model performance and generates reports.
    Compares RL-weighted strategies vs baseline top-3 strategies.
    """

    def __init__(self):
        """Initialize performance tracker."""
        self.weight_history: list[dict[str, Any]] = []
        self.performance_metrics: list[dict[str, Any]] = []

        logger.info("✅ RL Performance Tracker initialized")

    def track_weight_update(
        self, weights: dict[str, float], metadata: dict[str, Any] | None = None
    ):
        """
        Track strategy weight update.

        Args:
            weights: Strategy weights dictionary
            metadata: Optional metadata
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "weights": weights,
            "metadata": metadata or {},
        }

        self.weight_history.append(entry)

        # Keep last 1000 entries
        if len(self.weight_history) > 1000:
            self.weight_history = self.weight_history[-1000:]

        self.save_weight_history()

    def save_weight_history(self):
        """Save weight history to disk."""
        try:
            WEIGHT_HISTORY.write_text(
                json.dumps(
                    {"history": self.weight_history, "last_update": datetime.now(UTC).isoformat()},
                    indent=2,
                )
            )
        except Exception as e:
            logger.error(f"Failed to save weight history: {e}")

    def load_weight_history(self):
        """Load weight history from disk."""
        if WEIGHT_HISTORY.exists():
            try:
                data = json.loads(WEIGHT_HISTORY.read_text())
                self.weight_history = data.get("history", [])
            except Exception as e:
                logger.warning(f"Failed to load weight history: {e}")

    def compute_performance_metrics(self, days: int = 30) -> dict[str, Any]:
        """
        Compute performance metrics comparing RL vs baseline.

        Args:
            days: Number of days to analyze

        Returns:
            Performance metrics dictionary
        """
        metrics = {
            "period_days": days,
            "timestamp": datetime.now(UTC).isoformat(),
            "rl_performance": {},
            "baseline_performance": {},
            "comparison": {},
        }

        try:
            if not HAS_PANDAS:
                return metrics

            # Load performance data
            perf_csv = STATE / "performance_metrics.csv"
            if not perf_csv.exists():
                logger.warning("No performance metrics found")
                return metrics

            df = pd.read_csv(perf_csv)
            if len(df) == 0:
                return metrics

            if "ts" in df.columns:
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
                df = df.dropna(subset=["ts"]).sort_values("ts")
                cutoff = df["ts"].max() - timedelta(days=days)
                df = df[df["ts"] >= cutoff]

            if len(df) == 0:
                return metrics

            # Compute metrics
            if "equity" in df.columns:
                equity = pd.to_numeric(df["equity"], errors="coerce").dropna()
                if len(equity) > 1:
                    returns = equity.pct_change().dropna()

                    # Total return
                    total_return = (
                        (equity.iloc[-1] / equity.iloc[0] - 1) * 100 if len(equity) > 0 else 0.0
                    )

                    # Sharpe ratio
                    if "rolling_sharpe" in df.columns:
                        sharpe = pd.to_numeric(df["rolling_sharpe"], errors="coerce").dropna()
                        avg_sharpe = float(sharpe.mean()) if len(sharpe) > 0 else 0.0
                    else:
                        ret_std = returns.std(ddof=0)
                        avg_sharpe = (
                            float(returns.mean() / ret_std * np.sqrt(252))
                            if len(returns) > 0 and ret_std > 0
                            else 0.0
                        )

                    # Max drawdown
                    if "mdd_pct" in df.columns:
                        mdd = pd.to_numeric(df["mdd_pct"], errors="coerce").dropna()
                        max_dd = float(mdd.max()) if len(mdd) > 0 else 0.0
                    else:
                        peak = equity.expanding().max()
                        drawdown = (equity - peak) / peak * 100
                        max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0

                    # Volatility
                    vol_std = returns.std(ddof=0)
                    volatility = (
                        float(vol_std * np.sqrt(252) * 100)
                        if len(returns) > 0 and not np.isnan(vol_std)
                        else 0.0
                    )

                    metrics["rl_performance"] = {
                        "total_return_pct": total_return,
                        "sharpe_ratio": avg_sharpe,
                        "max_drawdown_pct": max_dd,
                        "volatility_pct": volatility,
                        "trades_count": len(df),
                    }

            # Load strategy performance for baseline comparison
            strategy_perf = STATE / "strategy_performance.json"
            if strategy_perf.exists():
                try:
                    strat_data = json.loads(strategy_perf.read_text())
                    ranked = strat_data.get("ranked_strategies", [])
                    if len(ranked) > 0:
                        top_strategy = ranked[0]
                        metrics["baseline_performance"] = {
                            "top_strategy": top_strategy.get("strategy", ""),
                            "top_sharpe": top_strategy.get("sharpe", 0.0),
                            "top_drawdown": top_strategy.get("drawdown", 0.0),
                        }

                        # Comparison
                        rl_sharpe = metrics["rl_performance"].get("sharpe_ratio", 0.0)
                        baseline_sharpe = metrics["baseline_performance"].get("top_sharpe", 0.0)

                        metrics["comparison"] = {
                            "sharpe_improvement": rl_sharpe - baseline_sharpe,
                            "sharpe_improvement_pct": ((rl_sharpe / baseline_sharpe - 1) * 100)
                            if baseline_sharpe > 0
                            else 0.0,
                            "rl_better": rl_sharpe > baseline_sharpe,
                        }
                except Exception as e:
                    logger.warning(f"Failed to load strategy performance: {e}")

        except Exception as e:
            logger.error(f"Error computing performance metrics: {e}")
            import traceback

            traceback.print_exc()

        return metrics

    def analyze_weight_evolution(self, days: int = 30) -> dict[str, Any]:
        """
        Analyze how strategy weights have evolved over time.

        Args:
            days: Number of days to analyze

        Returns:
            Evolution analysis
        """
        self.load_weight_history()

        if len(self.weight_history) == 0:
            return {"error": "No weight history available"}

        try:
            # Filter to recent period
            cutoff = datetime.now(UTC) - timedelta(days=days)
            recent_weights = [
                w
                for w in self.weight_history
                if datetime.fromisoformat(w["timestamp"].replace("Z", "+00:00")) >= cutoff
            ]

            if len(recent_weights) == 0:
                return {"error": "No weights in recent period"}

            # Compute average weights
            strategy_names = list(recent_weights[0]["weights"].keys())
            avg_weights = dict.fromkeys(strategy_names, 0.0)

            for entry in recent_weights:
                weights = entry.get("weights", {})
                for strategy in strategy_names:
                    avg_weights[strategy] += weights.get(strategy, 0.0)

            # Normalize
            total = sum(avg_weights.values())
            if total > 0:
                avg_weights = {k: v / total for k, v in avg_weights.items()}

            # Find most/least used strategies
            sorted_strategies = sorted(avg_weights.items(), key=lambda x: x[1], reverse=True)

            analysis = {
                "period_days": days,
                "samples": len(recent_weights),
                "average_weights": avg_weights,
                "top_strategy": sorted_strategies[0][0] if sorted_strategies else None,
                "top_weight": sorted_strategies[0][1] if sorted_strategies else 0.0,
                "bottom_strategy": sorted_strategies[-1][0] if sorted_strategies else None,
                "bottom_weight": sorted_strategies[-1][1] if sorted_strategies else 0.0,
                "weight_std": {
                    s: np.std([w["weights"].get(s, 0.0) for w in recent_weights])
                    for s in strategy_names
                },
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing weight evolution: {e}")
            return {"error": str(e)}

    def generate_report(self) -> dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Complete performance report
        """
        logger.info("📊 Generating RL performance report")

        # Compute metrics
        metrics_30d = self.compute_performance_metrics(days=30)
        metrics_7d = self.compute_performance_metrics(days=7)

        # Analyze weight evolution
        weight_evolution = self.analyze_weight_evolution(days=30)

        # Load training log
        training_log = STATE / "rl_training_log.json"
        training_info = {}
        if training_log.exists():
            try:
                data = json.loads(training_log.read_text())
                training_info = {
                    "last_training": data.get("last_training"),
                    "total_episodes": sum(
                        e.get("episodes", 0) for e in data.get("training_history", [])
                    ),
                    "recent_avg_reward": None,
                }
                history = data.get("training_history", [])
                if len(history) > 0:
                    recent = history[-5:]
                    avg_reward = sum(e.get("avg_reward", 0) for e in recent) / len(recent)
                    training_info["recent_avg_reward"] = avg_reward
            except Exception as e:
                logger.warning(f"Failed to load training log: {e}")

        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "performance_30d": metrics_30d,
            "performance_7d": metrics_7d,
            "weight_evolution": weight_evolution,
            "training_info": training_info,
            "summary": {
                "rl_sharpe_30d": metrics_30d.get("rl_performance", {}).get("sharpe_ratio", 0.0),
                "baseline_sharpe": metrics_30d.get("baseline_performance", {}).get(
                    "top_sharpe", 0.0
                ),
                "improvement": metrics_30d.get("comparison", {}).get("sharpe_improvement", 0.0),
                "rl_better": metrics_30d.get("comparison", {}).get("rl_better", False),
            },
        }

        # Save report
        try:
            PERFORMANCE_REPORT.write_text(json.dumps(report, indent=2))
            logger.info("✅ Performance report saved")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

        return report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="RL Performance Tracker")
    parser.add_argument("--report", action="store_true", help="Generate performance report")
    parser.add_argument("--track", action="store_true", help="Track current weight update")
    args = parser.parse_args()

    tracker = RLPerformanceTracker()

    if args.report:
        report = tracker.generate_report()
        print(json.dumps(report, indent=2))
    elif args.track:
        # Load current RL weights and track
        rl_weights_file = RUNTIME / "rl_strategy_weights.json"
        if rl_weights_file.exists():
            data = json.loads(rl_weights_file.read_text())
            weights = data.get("weights", {})
            metadata = data.get("metadata", {})
            tracker.track_weight_update(weights, metadata)
            print(f"✅ Tracked weight update: {weights}")
        else:
            print("⚠️  No RL weights file found")
    else:
        # Default: generate report
        report = tracker.generate_report()
        print("📊 Performance Report:")
        print(f"  RL Sharpe (30d): {report['summary']['rl_sharpe_30d']:.2f}")
        print(f"  Baseline Sharpe: {report['summary']['baseline_sharpe']:.2f}")
        print(f"  Improvement: {report['summary']['improvement']:.2f}")
        print(f"  RL Better: {report['summary']['rl_better']}")


if __name__ == "__main__":
    main()
