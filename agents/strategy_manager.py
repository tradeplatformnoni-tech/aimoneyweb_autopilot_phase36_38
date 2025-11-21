#!/usr/bin/env python3
"""
NeoLight Strategy Manager - Phase 3500-3700
===========================================
Manages multiple trading strategies simultaneously.
Allocates capital based on performance, tracks P&L per strategy,
and automatically retires underperforming strategies.
"""

import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

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

LOG_FILE = LOGS / "strategy_manager.log"
logger = logging.getLogger("strategy_manager")
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

# Advanced optimizers (optional imports - after logger setup)
try:
    from analytics.black_litterman_optimizer import BlackLittermanOptimizer

    HAS_BLACK_LITTERMAN = True
except ImportError:
    HAS_BLACK_LITTERMAN = False
    logger.warning("⚠️  Black-Litterman optimizer not available")

try:
    from analytics.hierarchical_risk_parity import HierarchicalRiskParity

    HAS_HRP = True
except ImportError:
    HAS_HRP = False
    logger.warning("⚠️  Hierarchical Risk Parity optimizer not available")

# Strategy definitions (from strategy_research.py)
STRATEGIES = {
    "turtle_trading": {"name": "Turtle Trading", "expected_sharpe": 1.5, "drawdown": 15},
    "mean_reversion_rsi": {"name": "RSI Mean Reversion", "expected_sharpe": 1.2, "drawdown": 10},
    "momentum_sma_crossover": {"name": "SMA Crossover", "expected_sharpe": 1.0, "drawdown": 20},
    "breakout_trading": {"name": "Breakout Trading", "expected_sharpe": 1.3, "drawdown": 12},
    "pairs_trading": {"name": "Pairs Trading", "expected_sharpe": 1.8, "drawdown": 8},
    "macd_momentum": {"name": "MACD Momentum", "expected_sharpe": 1.1, "drawdown": 15},
    "bollinger_bands": {"name": "Bollinger Bands", "expected_sharpe": 1.4, "drawdown": 10},
    "vix_strategy": {"name": "VIX Strategy", "expected_sharpe": 1.6, "drawdown": 25},
}

STRATEGY_PERFORMANCE_FILE = STATE / "strategy_performance.json"
STRATEGY_ALLOCATIONS_FILE = RUNTIME / "strategy_allocations.json"


class StrategyManager:
    """
    Manages multiple trading strategies with dynamic capital allocation.
    """

    def __init__(self):
        """Initialize strategy manager."""
        self.strategies = STRATEGIES.copy()
        self.performance = self.load_performance()
        logger.info(f"✅ StrategyManager initialized with {len(self.strategies)} strategies")

    def load_performance(self) -> dict[str, dict[str, Any]]:
        """Load strategy performance history."""
        if STRATEGY_PERFORMANCE_FILE.exists():
            try:
                data = json.loads(STRATEGY_PERFORMANCE_FILE.read_text())
                return data.get("strategy_performance", {})
            except Exception as e:
                logger.warning(f"⚠️  Error loading performance: {e}")
        return {}

    def save_performance(self):
        """Save strategy performance to file."""
        try:
            data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "strategy_performance": self.performance,
            }
            STRATEGY_PERFORMANCE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving performance: {e}")

    def update_strategy_pnl(self, strategy_name: str, pnl: float, trade_count: int = 1):
        """Update P&L for a strategy."""
        if strategy_name not in self.performance:
            self.performance[strategy_name] = {
                "total_pnl": 0.0,
                "trade_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "last_updated": datetime.now(UTC).isoformat(),
            }

        perf = self.performance[strategy_name]
        perf["total_pnl"] += pnl
        perf["trade_count"] += trade_count

        if pnl > 0:
            perf["win_count"] += trade_count
        elif pnl < 0:
            perf["loss_count"] += trade_count

        perf["last_updated"] = datetime.now(UTC).isoformat()
        self.save_performance()

    def calculate_strategy_sharpe(self, strategy_name: str, lookback_days: int = 30) -> float:
        """Calculate Sharpe ratio for a strategy."""
        if strategy_name not in self.performance:
            return 0.0

        perf = self.performance[strategy_name]
        if perf.get("trade_count", 0) < 10:
            # Use expected Sharpe if insufficient data
            return self.strategies.get(strategy_name, {}).get("expected_sharpe", 1.0)

        # Simplified Sharpe calculation
        win_rate = perf.get("win_count", 0) / max(1, perf.get("trade_count", 1))
        avg_pnl = perf.get("total_pnl", 0.0) / max(1, perf.get("trade_count", 1))

        # Estimate Sharpe from win rate and avg P&L
        if avg_pnl > 0:
            sharpe = win_rate * 2.0  # Simplified estimate
        else:
            sharpe = 0.0

        return max(0.0, min(sharpe, 3.0))  # Cap at 3.0

    def rank_strategies(self) -> list[tuple[str, float]]:
        """Rank strategies by performance (Sharpe ratio)."""
        ranked = []

        for strategy_name in self.strategies.keys():
            sharpe = self.calculate_strategy_sharpe(strategy_name)
            ranked.append((strategy_name, sharpe))

        # Sort by Sharpe (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def allocate_capital(
        self, total_capital: float, min_allocation: float = 0.05, max_allocation: float = 0.40
    ) -> dict[str, float]:
        """
        Allocate capital across strategies based on performance.
        Uses Sharpe ratio weighting with min/max constraints.
        """
        ranked = self.rank_strategies()

        if not ranked:
            # Equal allocation if no performance data
            n = len(self.strategies)
            equal_weight = 1.0 / n
            return dict.fromkeys(self.strategies.keys(), equal_weight)

        # Calculate weights based on Sharpe ratios
        sharpe_values = [sharpe for _, sharpe in ranked]
        total_sharpe = sum(max(0.1, s) for s in sharpe_values)  # Minimum 0.1 to avoid zero

        weights = {}
        for strategy_name, sharpe in ranked:
            # Weight proportional to Sharpe
            weight = max(0.1, sharpe) / total_sharpe if total_sharpe > 0 else 1.0 / len(ranked)

            # Apply min/max constraints
            weight = max(min_allocation, min(max_allocation, weight))
            weights[strategy_name] = weight

        # Normalize to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # Save allocations
        try:
            allocation_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "total_capital": total_capital,
                "allocations": weights,
                "ranked_strategies": [
                    {"strategy": name, "sharpe": sharpe} for name, sharpe in ranked
                ],
                "optimization_method": "sharpe",
            }
            STRATEGY_ALLOCATIONS_FILE.write_text(json.dumps(allocation_data, indent=2))
            logger.info(f"📊 Capital allocated across {len(weights)} strategies (Sharpe weighting)")
        except Exception as e:
            logger.error(f"❌ Error saving allocations: {e}")

        return weights

    def should_retire_strategy(
        self, strategy_name: str, min_trades: int = 20, min_sharpe: float = 0.5
    ) -> bool:
        """Determine if a strategy should be retired."""
        if strategy_name not in self.performance:
            return False

        perf = self.performance[strategy_name]

        # Need minimum trades to evaluate
        if perf.get("trade_count", 0) < min_trades:
            return False

        sharpe = self.calculate_strategy_sharpe(strategy_name)

        # Retire if Sharpe below threshold
        if sharpe < min_sharpe:
            logger.warning(f"⚠️  Strategy {strategy_name} underperforming (Sharpe: {sharpe:.2f})")
            return True

        return False

    def get_active_strategies(self) -> list[str]:
        """Get list of active (non-retired) strategies."""
        active = []

        for strategy_name in self.strategies.keys():
            if not self.should_retire_strategy(strategy_name):
                active.append(strategy_name)

        # Always return at least top 3 strategies
        if len(active) < 3:
            ranked = self.rank_strategies()
            active = [name for name, _ in ranked[:3]]

        return active

    def calculate_strategy_correlation(self) -> dict[str, Any]:
        """
        Calculate correlation matrix between strategies.
        Enhanced for Phase 3500-3700.
        """
        if not HAS_PANDAS:
            return {}

        try:
            returns_df = self.build_strategy_returns_dataframe()

            if returns_df is None or returns_df.empty:
                return {}

            # Calculate correlation matrix
            corr_matrix = returns_df.corr().fillna(0.0)

            # Find highly correlated strategy pairs
            highly_correlated = []
            strategies = list(corr_matrix.columns)

            for i, strat1 in enumerate(strategies):
                for strat2 in strategies[i + 1 :]:
                    corr = corr_matrix.loc[strat1, strat2]
                    if abs(corr) > 0.7:  # High correlation threshold
                        highly_correlated.append(
                            {"strategy1": strat1, "strategy2": strat2, "correlation": float(corr)}
                        )

            return {
                "correlation_matrix": corr_matrix.to_dict(),
                "highly_correlated_pairs": highly_correlated,
                "diversification_score": 1.0
                - abs(corr_matrix.mean().mean()),  # Higher = better diversification
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.warning(f"⚠️  Error calculating strategy correlation: {e}")
            return {}

    def allocate_capital_with_correlation(
        self,
        total_capital: float,
        max_correlation: float = 0.7,
        min_allocation: float = 0.05,
        max_allocation: float = 0.40,
    ) -> dict[str, float]:
        """
        Allocate capital considering strategy correlations.
        Reduces allocation to highly correlated strategies.
        Enhanced for Phase 3500-3700.
        """
        # Get correlation data
        corr_data = self.calculate_strategy_correlation()
        highly_correlated = corr_data.get("highly_correlated_pairs", [])

        # Get base allocations
        allocations = self.allocate_capital_advanced(total_capital, method="auto")

        # Reduce allocations for highly correlated strategies
        for pair in highly_correlated:
            strat1 = pair["strategy1"]
            strat2 = pair["strategy2"]
            corr = abs(pair["correlation"])

            if corr > max_correlation:
                # Reduce allocation to the lower-performing strategy
                sharpe1 = self.calculate_strategy_sharpe(strat1)
                sharpe2 = self.calculate_strategy_sharpe(strat2)

                if sharpe1 < sharpe2:
                    # Reduce allocation to strat1
                    allocations[strat1] = allocations.get(strat1, 0) * 0.7  # Reduce by 30%
                else:
                    # Reduce allocation to strat2
                    allocations[strat2] = allocations.get(strat2, 0) * 0.7

        # Normalize after correlation adjustments
        total_weight = sum(allocations.values())
        if total_weight > 0:
            allocations = {k: v / total_weight for k, v in allocations.items()}

        # Ensure min/max constraints
        for strategy_name in allocations.keys():
            allocations[strategy_name] = max(
                min_allocation, min(max_allocation, allocations[strategy_name])
            )

        # Normalize again
        total_weight = sum(allocations.values())
        if total_weight > 0:
            allocations = {k: v / total_weight for k, v in allocations.items()}

        logger.info(
            f"📊 Correlation-adjusted allocations computed (diversification score: {corr_data.get('diversification_score', 0):.3f})"
        )

        return allocations

    def build_strategy_returns_dataframe(self, lookback_days: int = 90) -> pd.DataFrame | None:
        """
        Build strategy returns DataFrame from performance data.
        Creates synthetic returns based on P&L and trade activity.

        Args:
            lookback_days: Number of days to look back for returns

        Returns:
            DataFrame with strategy returns, or None if insufficient data
        """
        if not HAS_PANDAS:
            return None

        try:
            strategy_returns = {}
            min_trades_needed = 5  # Minimum trades to create meaningful returns

            for strategy_name in self.strategies.keys():
                perf = self.performance.get(strategy_name, {})
                trade_count = perf.get("trade_count", 0)
                total_pnl = perf.get("total_pnl", 0.0)

                if trade_count < min_trades_needed:
                    # Use expected performance for strategies with no data
                    expected_sharpe = self.strategies[strategy_name].get("expected_sharpe", 1.0)
                    # Estimate daily return from Sharpe (assuming 15% vol)
                    daily_vol = 0.15 / np.sqrt(252)  # Annual vol to daily
                    daily_return = expected_sharpe * daily_vol  # Simplified
                    returns = [daily_return] * lookback_days
                else:
                    # Calculate returns from actual performance
                    avg_return_per_trade = total_pnl / max(trade_count, 1)

                    # Convert to percentage return (normalize by typical trade size)
                    # Assume average trade is 1% of capital
                    base_capital = 100000.0
                    avg_trade_size = base_capital * 0.01  # 1% per trade

                    if avg_trade_size > 0:
                        return_per_trade = avg_return_per_trade / avg_trade_size
                    else:
                        return_per_trade = 0.0

                    # Create return series (distribute returns across days)
                    # Simulate daily returns from trade returns
                    trades_per_day = max(1, trade_count // lookback_days)
                    daily_return = return_per_trade / trades_per_day if trades_per_day > 0 else 0.0

                    # Add some noise to make it realistic
                    noise = np.random.normal(0, abs(daily_return) * 0.3, lookback_days)
                    returns = [daily_return + n for n in noise]

                strategy_returns[strategy_name] = returns

            # Convert to DataFrame
            if strategy_returns:
                max_len = max(len(returns) for returns in strategy_returns.values())
                # Pad all to same length
                padded_returns = {}
                for name, returns in strategy_returns.items():
                    if len(returns) < max_len:
                        returns = returns + [returns[-1] if returns else 0.0] * (
                            max_len - len(returns)
                        )
                    padded_returns[name] = returns[:max_len]

                # Create DataFrame with dates
                dates = pd.date_range(end=datetime.now(UTC), periods=max_len, freq="D")
                df = pd.DataFrame(padded_returns, index=dates)

                # Convert returns to prices (cumulative product)
                prices_df = (1 + df).cumprod() * 100  # Start at 100

                return prices_df

            return None

        except Exception as e:
            logger.warning(f"⚠️  Error building strategy returns: {e}")
            return None

    def allocate_capital_advanced(
        self,
        total_capital: float,
        method: str = "auto",
        min_allocation: float = 0.05,
        max_allocation: float = 0.40,
    ) -> dict[str, float]:
        """
        Allocate capital using advanced optimization methods.

        Args:
            total_capital: Total capital to allocate
            method: "black_litterman", "hrp", "sharpe", or "auto" (tries BL -> HRP -> Sharpe)
            min_allocation: Minimum allocation per strategy
            max_allocation: Maximum allocation per strategy

        Returns:
            Dictionary of {strategy: allocation}
        """
        # Build strategy returns DataFrame
        returns_df = self.build_strategy_returns_dataframe()

        if returns_df is None or len(returns_df) < 30:
            # Insufficient data for advanced optimizers
            logger.info("📊 Insufficient data for advanced optimizers, using Sharpe weighting")
            return self.allocate_capital(total_capital, min_allocation, max_allocation)

        # Try advanced optimizers based on method
        if method == "auto":
            # Try Black-Litterman first, then HRP, then Sharpe
            methods_to_try = ["black_litterman", "hrp", "sharpe"]
        else:
            methods_to_try = [method, "sharpe"]  # Fallback to Sharpe

        for opt_method in methods_to_try:
            try:
                if opt_method == "black_litterman" and HAS_BLACK_LITTERMAN:
                    logger.info("🧠 Using Black-Litterman optimization...")
                    optimizer = BlackLittermanOptimizer(returns_df, risk_free_rate=0.02, tau=0.05)

                    # Create views from strategy performance (top strategies get higher expected returns)
                    ranked = self.rank_strategies()
                    views = {}
                    view_confidence = {}

                    # Top 3 strategies get optimistic views
                    for i, (strategy_name, sharpe) in enumerate(ranked[:3]):
                        if strategy_name in returns_df.columns:
                            # Expected return based on Sharpe (assume 15% vol)
                            expected_vol = 0.15
                            expected_return = sharpe * expected_vol if sharpe > 0 else 0.10
                            views[strategy_name] = expected_return
                            view_confidence[strategy_name] = 0.3  # Moderate confidence

                    weights = optimizer.optimize(
                        views=views if views else None,
                        view_confidence=view_confidence if view_confidence else None,
                    )

                    if weights:
                        # Apply min/max constraints
                        constrained_weights = {}
                        for strategy_name, weight in weights.items():
                            constrained_weight = max(min_allocation, min(max_allocation, weight))
                            constrained_weights[strategy_name] = constrained_weight

                        # Normalize
                        total_weight = sum(constrained_weights.values())
                        if total_weight > 0:
                            constrained_weights = {
                                k: v / total_weight for k, v in constrained_weights.items()
                            }

                        # Ensure all strategies have allocations
                        for strategy_name in self.strategies.keys():
                            if strategy_name not in constrained_weights:
                                constrained_weights[strategy_name] = min_allocation

                        # Normalize again after adding missing strategies
                        total_weight = sum(constrained_weights.values())
                        if total_weight > 0:
                            constrained_weights = {
                                k: v / total_weight for k, v in constrained_weights.items()
                            }

                        logger.info("✅ Black-Litterman optimization complete")
                        return constrained_weights

                elif opt_method == "hrp" and HAS_HRP:
                    logger.info("🌳 Using Hierarchical Risk Parity optimization...")
                    optimizer = HierarchicalRiskParity(returns_df)
                    weights = optimizer.optimize()

                    if weights:
                        # Apply min/max constraints
                        constrained_weights = {}
                        for strategy_name, weight in weights.items():
                            constrained_weight = max(min_allocation, min(max_allocation, weight))
                            constrained_weights[strategy_name] = constrained_weight

                        # Normalize
                        total_weight = sum(constrained_weights.values())
                        if total_weight > 0:
                            constrained_weights = {
                                k: v / total_weight for k, v in constrained_weights.items()
                            }

                        # Ensure all strategies have allocations
                        for strategy_name in self.strategies.keys():
                            if strategy_name not in constrained_weights:
                                constrained_weights[strategy_name] = min_allocation

                        # Normalize again
                        total_weight = sum(constrained_weights.values())
                        if total_weight > 0:
                            constrained_weights = {
                                k: v / total_weight for k, v in constrained_weights.items()
                            }

                        logger.info("✅ HRP optimization complete")
                        return constrained_weights

                elif opt_method == "sharpe":
                    # Fallback to Sharpe weighting
                    return self.allocate_capital(total_capital, min_allocation, max_allocation)

            except Exception as e:
                logger.warning(f"⚠️  {opt_method} optimization failed: {e}, trying next method...")
                continue

        # Ultimate fallback
        logger.warning("⚠️  All optimization methods failed, using equal weights")
        n = len(self.strategies)
        equal_weight = 1.0 / n
        return dict.fromkeys(self.strategies.keys(), equal_weight)


def main():
    """Main strategy manager loop."""
    logger.info("🚀 Strategy Manager starting...")

    manager = StrategyManager()
    update_interval = int(
        os.getenv("NEOLIGHT_STRATEGY_MANAGER_INTERVAL", "300")
    )  # Default 5 minutes

    while True:
        try:
            # Load current portfolio equity
            portfolio_file = STATE / "portfolio.json"
            equity = 100000.0  # Default

            if portfolio_file.exists():
                try:
                    portfolio = json.loads(portfolio_file.read_text())
                    equity = float(portfolio.get("equity", 100000.0))
                except Exception as e:
                    logger.warning(f"⚠️  Error loading portfolio: {e}")

            # Reload performance data for fresh calculations
            manager.performance = manager.load_performance()

            # Choose optimization method (from environment or default to auto)
            optimization_method = os.getenv("NEOLIGHT_STRATEGY_OPTIMIZATION_METHOD", "auto")
            # Options: "auto" (tries BL -> HRP -> Sharpe), "black_litterman", "hrp", "sharpe"
            used_method = "sharpe"

            if optimization_method != "sharpe":
                allocations = manager.allocate_capital_advanced(
                    equity, method=optimization_method, min_allocation=0.05, max_allocation=0.40
                )
                # Determine which method was actually used
                if HAS_BLACK_LITTERMAN and optimization_method in ["auto", "black_litterman"]:
                    used_method = "black_litterman"
                elif HAS_HRP and optimization_method in ["auto", "hrp"]:
                    used_method = "hierarchical_risk_parity"
                else:
                    used_method = "sharpe"
            else:
                # Use simple Sharpe weighting
                allocations = manager.allocate_capital(equity)
                used_method = "sharpe"

            # Save allocations with method info
            try:
                ranked = manager.rank_strategies()
                allocation_data = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "total_capital": equity,
                    "allocations": allocations,
                    "ranked_strategies": [
                        {"strategy": name, "sharpe": sharpe} for name, sharpe in ranked
                    ],
                    "optimization_method": used_method,
                }
                STRATEGY_ALLOCATIONS_FILE.write_text(json.dumps(allocation_data, indent=2))
                logger.info(
                    f"📊 Capital allocated across {len(allocations)} strategies ({used_method})"
                )
            except Exception as e:
                logger.error(f"❌ Error saving allocations: {e}")

            # Get active strategies
            active = manager.get_active_strategies()

            logger.info(f"✅ Active strategies: {', '.join(active)}")
            logger.info(f"📊 Capital allocations: {allocations}")

            # Update strategy performance file with active strategies
            try:
                perf_data = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "active_strategies": active,
                    "strategy_performance": manager.performance,
                    "allocations": allocations,
                }
                STRATEGY_PERFORMANCE_FILE.write_text(json.dumps(perf_data, indent=2))
            except Exception as e:
                logger.error(f"❌ Error saving strategy data: {e}")

            # Sleep before next update
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Strategy Manager stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in strategy manager loop: {e}")
            traceback.print_exc()
            time.sleep(60)  # Wait 1 minute before retrying on error


if __name__ == "__main__":
    main()
