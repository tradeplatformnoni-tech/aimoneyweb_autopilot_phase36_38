#!/usr/bin/env python3
"""
NeoLight Strategy Performance Tracker - Phase 3500-3700
========================================================
Tracks P&L per strategy, calculates strategy-specific metrics,
and provides automatic strategy scoring.
"""

import argparse
import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "strategy_performance.log"
logger = logging.getLogger("strategy_performance")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

PERFORMANCE_FILE = STATE / "strategy_performance.json"
PNL_HISTORY_FILE = STATE / "pnl_history.csv"


class StrategyPerformanceTracker:
    """
    Tracks performance metrics for each trading strategy.
    """

    def __init__(self):
        """Initialize performance tracker."""
        self.performance = self.load_performance()
        logger.info("✅ StrategyPerformanceTracker initialized")

    def load_performance(self) -> dict[str, dict[str, Any]]:
        """Load strategy performance from file."""
        if PERFORMANCE_FILE.exists():
            try:
                data = json.loads(PERFORMANCE_FILE.read_text())
                return data.get("strategy_performance", {})
            except Exception as e:
                logger.warning(f"⚠️  Error loading performance: {e}")
        return {}

    def save_performance(self):
        """Save performance data to file."""
        try:
            data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "strategy_performance": self.performance,
            }
            PERFORMANCE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving performance: {e}")

    def calculate_strategy_metrics(self, strategy_name: str) -> dict[str, Any]:
        """Calculate comprehensive metrics for a strategy."""
        if strategy_name not in self.performance:
            return {
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "max_drawdown": 0.0,
                "total_pnl": 0.0,
                "trade_count": 0,
            }

        perf = self.performance[strategy_name]
        trade_count = perf.get("trade_count", 0)
        win_count = perf.get("win_count", 0)
        total_pnl = perf.get("total_pnl", 0.0)

        win_rate = win_count / max(1, trade_count)
        avg_return = total_pnl / max(1, trade_count)

        # Estimate Sharpe from win rate and avg return
        if avg_return > 0 and trade_count >= 10:
            sharpe = win_rate * 2.0  # Simplified estimate
        else:
            sharpe = 0.0

        return {
            "sharpe_ratio": max(0.0, min(sharpe, 3.0)),
            "win_rate": win_rate,
            "avg_return": avg_return,
            "max_drawdown": perf.get("max_drawdown", 0.0),
            "total_pnl": total_pnl,
            "trade_count": trade_count,
            "win_count": win_count,
            "loss_count": perf.get("loss_count", 0),
        }

    def update_from_trades(self):
        """Update strategy performance from trade history."""
        if not PNL_HISTORY_FILE.exists() or not HAS_PANDAS:
            return

        try:
            df = pd.read_csv(PNL_HISTORY_FILE)
            if len(df) == 0:
                return

            # Group trades by strategy (if strategy column exists)
            # For now, we'll need to infer strategy from trade characteristics
            # This is a simplified approach - in production, trades should be tagged with strategy

            logger.info(f"📊 Processing {len(df)} trades for strategy performance")

            # If we have strategy tags, use them
            # Otherwise, we'll need to infer from trade patterns (future enhancement)

        except Exception as e:
            logger.warning(f"⚠️  Error updating from trades: {e}")

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {"timestamp": datetime.now(UTC).isoformat(), "strategies": {}}

        for strategy_name in self.performance.keys():
            metrics = self.calculate_strategy_metrics(strategy_name)
            report["strategies"][strategy_name] = metrics

        # Rank strategies
        ranked = sorted(
            report["strategies"].items(), key=lambda x: x[1]["sharpe_ratio"], reverse=True
        )

        report["ranked_strategies"] = [{"strategy": name, **metrics} for name, metrics in ranked]

        return report

    def save_report(self):
        """Save performance report to file."""
        report = self.generate_report()

        report_file = STATE / "strategy_performance_report.json"
        try:
            report_file.write_text(json.dumps(report, indent=2))
            logger.info(f"✅ Performance report saved to {report_file}")
        except Exception as e:
            logger.error(f"❌ Error saving report: {e}")


def _run_once(tracker: StrategyPerformanceTracker) -> None:
    """Execute a single performance update cycle."""
    tracker.performance = tracker.load_performance()
    tracker.update_from_trades()
    tracker.save_report()
    logger.info("✅ Performance tracking complete")


def main():
    """Main performance tracker loop."""
    parser = argparse.ArgumentParser(description="NeoLight Strategy Performance Tracker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single update cycle and exit.",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Alias for --once; convenience flag for nightly schedulers.",
    )
    args = parser.parse_args()

    logger.info("🚀 Strategy Performance Tracker starting...")

    tracker = StrategyPerformanceTracker()
    update_interval = int(
        os.getenv("NEOLIGHT_STRATEGY_PERFORMANCE_INTERVAL", "300")
    )  # Default 5 minutes

    if args.once or args.daily:
        _run_once(tracker)
        return

    while True:
        try:
            _run_once(tracker)
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Strategy Performance Tracker stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in performance tracker loop: {e}")
            traceback.print_exc()
            time.sleep(60)  # Wait 1 minute before retrying on error


if __name__ == "__main__":
    main()
