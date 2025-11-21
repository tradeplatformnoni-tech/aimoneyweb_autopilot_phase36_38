#!/usr/bin/env python3
"""
NeoLight Strategy Portfolio Optimizer - Phase 3500-3700
======================================================
Optimizes strategy weights using portfolio optimization techniques.
Similar to portfolio_optimizer.py but for strategies instead of assets.
"""

import json
import logging
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path

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

LOG_FILE = LOGS / "strategy_portfolio.log"
logger = logging.getLogger("strategy_portfolio")
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


class StrategyPortfolioOptimizer:
    """
    Optimizes strategy weights using portfolio optimization.
    Treats strategies as assets and optimizes their allocation.
    """

    def __init__(self, strategy_returns: dict[str, list[float]], risk_free_rate: float = 0.02):
        """
        Initialize strategy portfolio optimizer.

        Args:
            strategy_returns: Dict of {strategy_name: [returns...]}
            risk_free_rate: Annual risk-free rate
        """
        self.strategy_returns = strategy_returns
        self.risk_free_rate = risk_free_rate
        self.strategy_names = list(strategy_returns.keys())

        if HAS_PANDAS:
            # Convert to DataFrame
            max_len = max(len(returns) for returns in strategy_returns.values())
            data = {}
            for name, returns in strategy_returns.items():
                # Pad with zeros if needed
                padded = returns + [0.0] * (max_len - len(returns))
                data[name] = padded[:max_len]
            self.returns_df = pd.DataFrame(data)
        else:
            self.returns_df = None

        logger.info(
            f"✅ StrategyPortfolioOptimizer initialized for {len(self.strategy_names)} strategies"
        )

    def calculate_strategy_covariance(self) -> np.ndarray:
        """Calculate covariance matrix between strategies."""
        if self.returns_df is None or len(self.returns_df) < 10:
            # Return identity matrix if insufficient data
            n = len(self.strategy_names)
            return np.eye(n)

        try:
            returns = self.returns_df.pct_change().dropna()
            if len(returns) < 10:
                return np.eye(len(self.strategy_names))

            cov_matrix = returns.cov().values * 252  # Annualize
            return cov_matrix
        except Exception as e:
            logger.warning(f"⚠️  Error calculating covariance: {e}")
            return np.eye(len(self.strategy_names))

    def calculate_strategy_returns(self) -> np.ndarray:
        """Calculate mean returns for each strategy."""
        if self.returns_df is None:
            # Return equal returns if no data
            return np.ones(len(self.strategy_names)) * 0.10  # 10% default

        try:
            mean_returns = self.returns_df.mean().values * 252  # Annualize
            return mean_returns
        except Exception as e:
            logger.warning(f"⚠️  Error calculating returns: {e}")
            return np.ones(len(self.strategy_names)) * 0.10

    def optimize_sharpe(self) -> dict[str, float]:
        """
        Optimize strategy weights to maximize Sharpe ratio.
        Uses Markowitz mean-variance optimization.
        """
        if len(self.strategy_names) == 0:
            return {}

        try:
            mean_returns = self.calculate_strategy_returns()
            cov_matrix = self.calculate_strategy_covariance()
            n = len(self.strategy_names)

            # Use inverse covariance method for maximum Sharpe
            inv_cov = np.linalg.pinv(cov_matrix)
            excess_returns = mean_returns - self.risk_free_rate

            numerator = inv_cov.dot(excess_returns)
            denominator = np.ones(n).dot(inv_cov).dot(excess_returns)

            if abs(denominator) < 1e-10:
                # Fallback to equal weights
                logger.warning("⚠️  Sharpe optimization unstable, using equal weights")
                equal_weight = 1.0 / n
                return dict.fromkeys(self.strategy_names, equal_weight)

            weights = numerator / denominator
            weights = np.clip(weights, 0, 1)  # No negative weights
            weights /= np.sum(weights)  # Normalize

            # Convert to dictionary
            optimal_weights = dict(zip(self.strategy_names, weights))

            # Calculate portfolio metrics
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (
                (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            )

            logger.info(
                f"📈 Strategy Portfolio Sharpe: {sharpe:.3f} | Return: {portfolio_return:.2%} | Vol: {portfolio_vol:.2%}"
            )

            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in Sharpe optimization: {e}")
            traceback.print_exc()
            # Fallback to equal weights
            equal_weight = 1.0 / len(self.strategy_names)
            return dict.fromkeys(self.strategy_names, equal_weight)

    def risk_parity_weights(self) -> dict[str, float]:
        """Compute equal-risk contribution portfolio."""
        try:
            cov_matrix = self.calculate_strategy_covariance()
            vol = np.sqrt(np.diag(cov_matrix))
            vol = np.maximum(vol, 1e-6)  # Avoid division by zero

            # Inverse volatility weighting
            inv_vol = 1.0 / vol
            weights = inv_vol / np.sum(inv_vol)

            optimal_weights = dict(zip(self.strategy_names, weights))
            logger.info("⚖️  Strategy risk parity weights computed")
            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in risk parity: {e}")
            equal_weight = 1.0 / len(self.strategy_names)
            return dict.fromkeys(self.strategy_names, equal_weight)


def load_strategy_returns() -> dict[str, list[float]]:
    """Load strategy returns from performance data."""
    perf_file = STATE / "strategy_performance.json"
    strategy_returns = {}

    if perf_file.exists():
        try:
            data = json.loads(perf_file.read_text())
            perf = data.get("strategy_performance", {})

            for strategy_name, stats in perf.items():
                # Estimate returns from P&L and trade count
                total_pnl = stats.get("total_pnl", 0.0)
                trade_count = stats.get("trade_count", 0)

                if trade_count > 0:
                    # Create synthetic returns from P&L
                    avg_return = total_pnl / (trade_count * 1000.0)  # Normalize
                    # Create return series (simplified)
                    returns = [avg_return] * min(trade_count, 30)  # Last 30 trades
                    strategy_returns[strategy_name] = returns

        except Exception as e:
            logger.warning(f"⚠️  Error loading strategy returns: {e}")

    return strategy_returns


def main():
    """Main strategy portfolio optimizer."""
    logger.info("🚀 Strategy Portfolio Optimizer starting...")

    # Load strategy returns
    strategy_returns = load_strategy_returns()

    if not strategy_returns:
        logger.warning("⚠️  No strategy returns data available, using default weights")
        return

    # Initialize optimizer
    optimizer = StrategyPortfolioOptimizer(strategy_returns, risk_free_rate=0.02)

    # Optimize for Sharpe
    optimal_weights = optimizer.optimize_sharpe()

    # Save to runtime
    output_file = RUNTIME / "strategy_portfolio_weights.json"
    try:
        output_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "method": "sharpe_optimization",
            "weights": optimal_weights,
        }
        output_file.write_text(json.dumps(output_data, indent=2))
        logger.info(f"✅ Strategy portfolio weights saved to {output_file}")
    except Exception as e:
        logger.error(f"❌ Error saving weights: {e}")


if __name__ == "__main__":
    main()
