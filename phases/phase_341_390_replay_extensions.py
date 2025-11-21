#!/usr/bin/env python3
"""
Phase 341-390: Replay Extensions - WORLD CLASS
==============================================
Einstein-level replay extensions:
- Advanced backtesting
- Walk-forward analysis
- Monte Carlo simulation
- Scenario analysis
- Paper-mode compatible
"""

import logging
import os
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
for p in [STATE, RUNTIME, LOGS]:
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "replay_extensions.log"
logger = logging.getLogger("replay_extensions")
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

# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    from utils.circuit_breaker import CircuitBreaker
    from utils.health_check import HealthCheck
    from utils.retry import retry_with_backoff
    from utils.state_manager import StateManager

    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False
    logger.warning("⚠️ World-class utilities not available")

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger.warning("⚠️ Pandas not available")

REPLAY_STATE_FILE = STATE / "replay_extensions_state.json"
PNL_HISTORY_FILE = STATE / "pnl_history.csv"


class ReplayExtensions:
    """World-class replay extensions engine."""

    def __init__(self):
        """Initialize replay extensions."""
        self.state_manager = None
        if HAS_WORLD_CLASS_UTILS:
            try:
                self.state_manager = StateManager(
                    REPLAY_STATE_FILE,
                    default_state={"last_replay": None, "scenarios": []},
                    backup_count=24,
                    backup_interval=3600.0,
                )
            except Exception as e:
                logger.warning(f"⚠️ StateManager init failed: {e}")
        logger.info("✅ ReplayExtensions initialized")

    def monte_carlo_simulation(
        self, returns: list[float], num_simulations: int = 1000, days: int = 252
    ) -> dict[str, Any]:
        """Run Monte Carlo simulation."""
        if not returns or len(returns) < 2:
            return {"error": "Insufficient data"}

        try:
            import numpy as np

            returns_array = np.array(returns)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)

            # Generate random paths
            final_values = []
            for _ in range(num_simulations):
                random_returns = np.random.normal(mean_return, std_return, days)
                final_value = 100000.0 * np.prod(1 + random_returns)
                final_values.append(final_value)

            final_values = np.array(final_values)

            return {
                "mean_final_value": float(np.mean(final_values)),
                "median_final_value": float(np.median(final_values)),
                "std_final_value": float(np.std(final_values)),
                "min_final_value": float(np.min(final_values)),
                "max_final_value": float(np.max(final_values)),
                "percentile_5": float(np.percentile(final_values, 5)),
                "percentile_95": float(np.percentile(final_values, 95)),
            }
        except Exception as e:
            logger.error(f"❌ Error in Monte Carlo simulation: {e}")
            return {"error": str(e)}

    def walk_forward_analysis(
        self,
        start_date: str,
        end_date: str,
        train_period_days: int = 180,
        test_period_days: int = 30,
    ) -> dict[str, Any]:
        """Perform walk-forward analysis."""
        if not HAS_PANDAS or not PNL_HISTORY_FILE.exists():
            return {"error": "No PnL history available"}

        try:
            df = pd.read_csv(PNL_HISTORY_FILE)
            df["date"] = pd.to_datetime(df.get("date", df.index))

            results = []
            current_date = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            while current_date < end:
                train_end = current_date + timedelta(days=train_period_days)
                test_end = train_end + timedelta(days=test_period_days)

                if test_end > end:
                    break

                train_data = df[(df["date"] >= current_date) & (df["date"] < train_end)]
                test_data = df[(df["date"] >= train_end) & (df["date"] < test_end)]

                if len(train_data) > 0 and len(test_data) > 0:
                    train_return = train_data["pnl"].sum() if "pnl" in train_data.columns else 0.0
                    test_return = test_data["pnl"].sum() if "pnl" in test_data.columns else 0.0

                    results.append(
                        {
                            "period": f"{current_date.date()} to {test_end.date()}",
                            "train_return": float(train_return),
                            "test_return": float(test_return),
                            "train_trades": len(train_data),
                            "test_trades": len(test_data),
                        }
                    )

                current_date = test_end

            return {
                "periods": results,
                "avg_train_return": sum([r["train_return"] for r in results]) / len(results)
                if results
                else 0.0,
                "avg_test_return": sum([r["test_return"] for r in results]) / len(results)
                if results
                else 0.0,
            }
        except Exception as e:
            logger.error(f"❌ Error in walk-forward analysis: {e}")
            return {"error": str(e)}

    def scenario_analysis(
        self, base_returns: list[float], scenarios: dict[str, float]
    ) -> dict[str, Any]:
        """Run scenario analysis."""
        results = {}

        for scenario_name, multiplier in scenarios.items():
            scenario_returns = [r * multiplier for r in base_returns]
            total_return = sum(scenario_returns)
            results[scenario_name] = {
                "total_return": total_return,
                "return_pct": (total_return / 100000.0) * 100 if total_return else 0.0,
            }

        return results


@world_class_agent("replay_extensions", state_file=REPLAY_STATE_FILE, paper_mode_only=True)
def main():
    """Main replay extensions loop."""
    logger.info("🚀 Replay Extensions starting...")

    replay = ReplayExtensions()

    # Monitor loop
    while True:
        try:
            time.sleep(3600)  # Run analysis every hour

            # Load PnL history for analysis
            if HAS_PANDAS and PNL_HISTORY_FILE.exists():
                try:
                    df = pd.read_csv(PNL_HISTORY_FILE)
                    if "pnl" in df.columns:
                        returns = df["pnl"].tolist()

                        # Run Monte Carlo simulation
                        mc_results = replay.monte_carlo_simulation(returns, num_simulations=100)
                        if "error" not in mc_results:
                            logger.info(
                                f"📊 Monte Carlo: Mean final value: ${mc_results.get('mean_final_value', 0):,.2f}"
                            )

                        # Run scenario analysis
                        scenarios = {"bull_market": 1.5, "bear_market": 0.5, "normal": 1.0}
                        scenario_results = replay.scenario_analysis(returns, scenarios)
                        logger.info(
                            f"📈 Scenario Analysis: {len(scenario_results)} scenarios analyzed"
                        )

                except Exception as e:
                    logger.error(f"❌ Error in replay analysis: {e}")

        except KeyboardInterrupt:
            logger.info("🛑 Replay Extensions stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in replay extensions loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
