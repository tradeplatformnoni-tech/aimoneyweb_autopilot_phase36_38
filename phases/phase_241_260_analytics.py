#!/usr/bin/env python3
"""
Phase 241-260: Advanced Analytics - WORLD CLASS
===============================================
Einstein-level analytics:
- Performance attribution
- Trade analysis
- Strategy performance breakdown
- Risk-adjusted returns
- Drawdown analysis
- Paper-mode compatible
"""

import logging
import math
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
for p in [STATE, RUNTIME, LOGS]:
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "analytics.log"
logger = logging.getLogger("analytics")
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

ANALYTICS_STATE_FILE = STATE / "analytics_state.json"
PNL_HISTORY_FILE = STATE / "pnl_history.csv"


class AdvancedAnalytics:
    """World-class analytics engine."""

    def __init__(self):
        """Initialize analytics engine."""
        self.state_manager = None
        if HAS_WORLD_CLASS_UTILS:
            try:
                self.state_manager = StateManager(
                    ANALYTICS_STATE_FILE,
                    default_state={"last_analysis": None, "metrics": {}},
                    backup_count=24,
                    backup_interval=3600.0,
                )
            except Exception as e:
                logger.warning(f"⚠️ StateManager init failed: {e}")
        logger.info("✅ AdvancedAnalytics initialized")

    def calculate_sharpe_ratio(self, returns: list[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0

        try:
            import numpy as np

            returns_array = np.array(returns)
            excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
            if np.std(excess_returns) == 0:
                return 0.0
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * math.sqrt(252)
            return float(sharpe) if not math.isnan(sharpe) else 0.0
        except Exception:
            return 0.0

    def calculate_max_drawdown(self, equity_series: list[float]) -> dict[str, float]:
        """Calculate maximum drawdown."""
        if not equity_series or len(equity_series) < 2:
            return {"max_drawdown": 0.0, "max_drawdown_pct": 0.0}

        peak = equity_series[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for value in equity_series:
            if value > peak:
                peak = value
            drawdown = peak - value
            drawdown_pct = drawdown / peak if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct

        return {"max_drawdown": max_dd, "max_drawdown_pct": max_dd_pct}

    def analyze_performance(self) -> dict[str, Any]:
        """Analyze overall performance."""
        if not HAS_PANDAS or not PNL_HISTORY_FILE.exists():
            return {"error": "No PnL history available"}

        try:
            df = pd.read_csv(PNL_HISTORY_FILE)

            if df.empty or "pnl" not in df.columns:
                return {"error": "Invalid PnL data"}

            returns = df["pnl"].tolist()
            total_pnl = sum(returns)
            win_rate = len([r for r in returns if r > 0]) / len(returns) if returns else 0.0

            sharpe = self.calculate_sharpe_ratio(returns)

            # Calculate equity curve
            equity_series = [100000.0]  # Starting equity
            for pnl in returns:
                equity_series.append(equity_series[-1] + pnl)

            drawdown = self.calculate_max_drawdown(equity_series)

            return {
                "total_pnl": total_pnl,
                "total_return_pct": (equity_series[-1] - equity_series[0]) / equity_series[0] * 100,
                "win_rate": win_rate,
                "sharpe_ratio": sharpe,
                "max_drawdown": drawdown["max_drawdown"],
                "max_drawdown_pct": drawdown["max_drawdown_pct"],
                "total_trades": len(returns),
                "winning_trades": len([r for r in returns if r > 0]),
                "losing_trades": len([r for r in returns if r < 0]),
            }
        except Exception as e:
            logger.error(f"❌ Error analyzing performance: {e}")
            return {"error": str(e)}

    def attribute_performance_by_strategy(self) -> dict[str, Any]:
        """Attribute performance by strategy."""
        if not HAS_PANDAS or not PNL_HISTORY_FILE.exists():
            return {}

        try:
            df = pd.read_csv(PNL_HISTORY_FILE)

            if df.empty or "strategy" not in df.columns:
                return {}

            attribution = {}
            for strategy in df["strategy"].unique():
                strategy_df = df[df["strategy"] == strategy]
                strategy_pnl = strategy_df["pnl"].sum()
                strategy_trades = len(strategy_df)
                strategy_win_rate = (
                    len(strategy_df[strategy_df["pnl"] > 0]) / strategy_trades
                    if strategy_trades > 0
                    else 0.0
                )

                attribution[strategy] = {
                    "total_pnl": float(strategy_pnl),
                    "trade_count": strategy_trades,
                    "win_rate": strategy_win_rate,
                    "avg_pnl": float(strategy_pnl / strategy_trades)
                    if strategy_trades > 0
                    else 0.0,
                }

            return attribution
        except Exception as e:
            logger.error(f"❌ Error attributing performance: {e}")
            return {}


@world_class_agent("analytics", state_file=ANALYTICS_STATE_FILE, paper_mode_only=True)
def main():
    """Main analytics loop."""
    logger.info("🚀 Advanced Analytics starting...")

    analytics = AdvancedAnalytics()

    # Analysis loop
    while True:
        try:
            time.sleep(300)  # Analyze every 5 minutes

            # Run performance analysis
            performance = analytics.analyze_performance()
            if "error" not in performance:
                logger.info(
                    f"📊 Performance: {performance.get('total_return_pct', 0):.2f}% return, "
                    f"Sharpe: {performance.get('sharpe_ratio', 0):.2f}, "
                    f"Win Rate: {performance.get('win_rate', 0):.1%}"
                )

            # Attribute by strategy
            attribution = analytics.attribute_performance_by_strategy()
            if attribution:
                logger.info(f"📈 Strategy Attribution: {len(attribution)} strategies")

        except KeyboardInterrupt:
            logger.info("🛑 Advanced Analytics stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in analytics loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
