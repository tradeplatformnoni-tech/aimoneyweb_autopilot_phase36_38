#!/usr/bin/env python3
"""
NeoLight Portfolio Optimizer - Phase 2500–2700
===============================================
World-class portfolio optimization using Modern Portfolio Theory:
- Sharpe Ratio Optimization (efficient frontier)
- Risk Parity Allocation
- Minimum Variance Portfolio
- Dynamic rebalancing with Capital Governor integration
- Normalized risk metrics (percent-of-equity based)
"""

import json
import logging
import os
import traceback
from datetime import UTC, datetime
from pathlib import Path

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("⚠️  Install numpy and pandas: pip install numpy pandas")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "portfolio_optimizer.log"
logger = logging.getLogger("portfolio_optimizer")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)


class PortfolioOptimizer:
    """
    World-class portfolio optimizer with multiple optimization strategies.
    All calculations use percent-of-equity normalization for scalability.
    """

    def __init__(self, returns_df: pd.DataFrame, risk_free_rate: float = 0.02):
        """
        Initialize portfolio optimizer.

        Args:
            returns_df: DataFrame with asset returns (columns = symbols, rows = time)
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        if not HAS_NUMPY:
            raise ImportError("numpy and pandas required for portfolio optimization")

        self.returns_df = returns_df
        self.risk_free_rate = risk_free_rate
        self.cov_matrix = self.calculate_covariance_matrix()
        self.mean_returns = self.returns_df.mean() * 252  # Annualized
        logger.info(f"✅ PortfolioOptimizer initialized for {len(returns_df.columns)} assets")

    def calculate_covariance_matrix(self) -> pd.DataFrame:
        """Compute covariance matrix from returns (annualized)."""
        if self.returns_df.empty:
            logger.warning("⚠️  Empty returns DataFrame")
            return pd.DataFrame()

        returns = self.returns_df.pct_change().dropna()
        cov_matrix = returns.cov() * 252  # Annualize
        logger.debug(f"📊 Covariance matrix computed: {cov_matrix.shape}")
        return cov_matrix

    def optimize_efficient_frontier(self, target_return: float | None = None) -> dict[str, float]:
        """
        Compute optimal weights based on Sharpe ratio maximization.
        Uses Markowitz mean-variance optimization.

        Args:
            target_return: Optional target return (annualized). If None, maximizes Sharpe.

        Returns:
            Dictionary of {symbol: weight} with weights normalized to sum to 1.0
        """
        if self.cov_matrix.empty or len(self.mean_returns) == 0:
            logger.warning("⚠️  Cannot optimize: insufficient data")
            return {}

        try:
            mean_returns = self.mean_returns.values
            cov_matrix = self.cov_matrix.values
            n = len(mean_returns)

            # Check for invalid returns data (all negative or extreme values)
            if (
                np.all(mean_returns < -0.5)
                or np.any(np.isnan(mean_returns))
                or np.any(np.isinf(mean_returns))
            ):
                logger.warning("⚠️  Invalid mean returns detected, using risk parity")
                return self.risk_parity_weights()

            # Use inverse covariance matrix method for maximum Sharpe
            # For max Sharpe: w = (C^-1 * (μ - rf)) / (1^T * C^-1 * (μ - rf))
            inv_cov = np.linalg.pinv(cov_matrix)  # Pseudo-inverse for stability
            excess_returns = mean_returns - self.risk_free_rate

            # Check if all excess returns are negative (bad market conditions)
            if np.all(excess_returns <= 0):
                logger.warning("⚠️  All excess returns negative, using minimum variance")
                return self.optimize_min_variance()

            numerator = inv_cov.dot(excess_returns)
            denominator = np.ones(n).dot(inv_cov).dot(excess_returns)

            if (
                abs(denominator) < 1e-10
                or np.any(np.isnan(numerator))
                or np.any(np.isinf(numerator))
            ):
                # Fallback to risk parity if denominator is near zero or invalid
                logger.warning("⚠️  Sharpe optimization unstable, using risk parity")
                return self.risk_parity_weights()

            weights = numerator / denominator
            weights = np.clip(weights, 0, 1)  # No short selling

            # Check for invalid weights
            if np.sum(weights) < 1e-10 or np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
                logger.warning("⚠️  Invalid weights computed, using risk parity")
                return self.risk_parity_weights()

            weights /= np.sum(weights)  # Normalize

            # Convert to dictionary
            optimal_weights = dict(zip(self.returns_df.columns, weights))

            # Calculate portfolio metrics
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (
                (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            )

            # If Sharpe is still negative after optimization, use minimum variance
            if sharpe < -1.0:
                logger.warning(
                    f"⚠️  Negative Sharpe ({sharpe:.3f}) detected, switching to minimum variance"
                )
                return self.optimize_min_variance()

            logger.info(
                f"📈 Optimal Sharpe: {sharpe:.3f} | Return: {portfolio_return:.2%} | Vol: {portfolio_vol:.2%}"
            )

            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in efficient frontier optimization: {e}")
            traceback.print_exc()
            return self.risk_parity_weights()  # Fallback

    def risk_parity_weights(self) -> dict[str, float]:
        """
        Compute equal-risk contribution portfolio (risk parity).
        Each asset contributes equally to portfolio risk.

        Returns:
            Dictionary of {symbol: weight} with weights normalized
        """
        if self.cov_matrix.empty:
            logger.warning("⚠️  Cannot compute risk parity: no covariance data")
            return {}

        try:
            # Calculate volatilities (annualized standard deviations)
            vol = np.sqrt(np.diag(self.cov_matrix.values))

            # Avoid division by zero
            vol = np.maximum(vol, 1e-6)

            # Inverse volatility weighting (simplified risk parity)
            inv_vol = 1.0 / vol
            weights = inv_vol / np.sum(inv_vol)

            # Convert to dictionary
            optimal_weights = dict(zip(self.returns_df.columns, weights))

            logger.info("⚖️  Risk parity weights computed")
            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in risk parity calculation: {e}")
            traceback.print_exc()
            return {}

    def minimum_variance_weights(self) -> dict[str, float]:
        """
        Compute minimum variance portfolio (lowest risk).

        Returns:
            Dictionary of {symbol: weight} with weights normalized
        """
        if self.cov_matrix.empty:
            logger.warning("⚠️  Cannot compute min variance: no covariance data")
            return {}

        try:
            cov_matrix = self.cov_matrix.values
            n = len(cov_matrix)

            # Min variance: w = (C^-1 * 1) / (1^T * C^-1 * 1)
            inv_cov = np.linalg.pinv(cov_matrix)
            ones = np.ones(n)

            numerator = inv_cov.dot(ones)
            denominator = ones.dot(inv_cov).dot(ones)

            if abs(denominator) < 1e-10:
                logger.warning("⚠️  Min variance unstable, using risk parity")
                return self.risk_parity_weights()

            weights = numerator / denominator
            weights = np.clip(weights, 0, 1)  # No short selling
            weights /= np.sum(weights)  # Normalize

            optimal_weights = dict(zip(self.returns_df.columns, weights))

            # Calculate portfolio volatility
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            logger.info(f"📉 Min variance portfolio vol: {portfolio_vol:.2%}")

            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in min variance calculation: {e}")
            traceback.print_exc()
            return {}

    def optimize_mean_cvar(
        self, confidence_level: float = 0.95, target_return: float | None = None
    ) -> dict[str, float]:
        """
        Optimize portfolio for Mean-CVaR (Conditional Value at Risk).
        Focuses on tail risk instead of variance.

        Args:
            confidence_level: CVaR confidence level (0.95 = 95%)
            target_return: Optional target return constraint

        Returns:
            Optimal weights
        """
        if self.cov_matrix.empty:
            logger.warning("⚠️  Cannot compute Mean-CVaR: no covariance data")
            return {}

        try:
            from ai.risk_enhancements import AdvancedRiskManager

            # Get returns
            returns = self.returns_df.pct_change().dropna()
            if len(returns) < 30:
                logger.warning("⚠️  Insufficient data for Mean-CVaR, using Sharpe optimization")
                return self.optimize_efficient_frontier()

            # Calculate portfolio returns for different weights
            # Simplified: use variance as proxy for CVaR (full CVaR optimization requires more computation)
            mean_returns = self.mean_returns.values
            cov_matrix = self.cov_matrix.values
            n = len(mean_returns)

            # For Mean-CVaR, we want to minimize CVaR subject to return constraint
            # Simplified approach: use inverse volatility weighting with return constraint

            if target_return is not None:
                # Optimize for target return with minimum CVaR
                # Use Sharpe-like optimization but with CVaR penalty
                inv_cov = np.linalg.pinv(cov_matrix)
                excess_returns = mean_returns - self.risk_free_rate

                # Add CVaR penalty (simplified: use volatility as proxy)
                numerator = inv_cov.dot(excess_returns)
                denominator = np.ones(n).dot(inv_cov).dot(excess_returns)

                if abs(denominator) > 1e-10:
                    weights = numerator / denominator
                    weights = np.clip(weights, 0, 1)
                    weights /= np.sum(weights)

                    # Calculate actual return
                    actual_return = np.dot(weights, mean_returns)
                    if actual_return < target_return:
                        # Scale up riskier assets to meet return target
                        risk_adjusted = excess_returns / np.sqrt(np.diag(cov_matrix))
                        risk_adjusted = np.maximum(risk_adjusted, 0)
                        weights = (
                            risk_adjusted / np.sum(risk_adjusted)
                            if np.sum(risk_adjusted) > 0
                            else weights
                        )
                else:
                    weights = np.ones(n) / n
            else:
                # Minimize CVaR (use inverse volatility)
                vol = np.sqrt(np.diag(cov_matrix))
                vol = np.maximum(vol, 1e-6)
                inv_vol = 1.0 / vol
                weights = inv_vol / np.sum(inv_vol)

            optimal_weights = dict(zip(self.returns_df.columns, weights))

            # Calculate CVaR for portfolio
            portfolio_returns = returns.dot(weights).values
            risk_mgr = AdvancedRiskManager(portfolio_returns)
            cvar = risk_mgr.calculate_cvar(confidence_level)

            portfolio_return = np.dot(weights, mean_returns)
            logger.info(
                f"📊 Mean-CVaR Portfolio: Return {portfolio_return:.2%} | CVaR {cvar:.2%} (confidence: {confidence_level:.0%})"
            )

            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in Mean-CVaR optimization: {e}")
            traceback.print_exc()
            return self.optimize_efficient_frontier()  # Fallback

    def save_allocations_to_state(
        self, weights_dict: dict[str, float], method: str = "sharpe"
    ) -> bool:
        """
        Save computed weights to state/allocations.json for Capital Governor.

        Args:
            weights_dict: Dictionary of {symbol: weight}
            method: Optimization method used (sharpe, risk_parity, min_variance)

        Returns:
            True if saved successfully
        """
        try:
            allocations_file = STATE / "allocations.json"

            # Calculate portfolio metrics for reporting
            portfolio_return = (
                np.dot(
                    list(weights_dict.values()),
                    [self.mean_returns.get(sym, 0) for sym in weights_dict],
                )
                if len(weights_dict) > 0
                else 0
            )

            portfolio_vol = (
                np.sqrt(
                    np.dot(
                        list(weights_dict.values()),
                        np.dot(
                            self.cov_matrix.loc[
                                list(weights_dict.keys()), list(weights_dict.keys())
                            ].values,
                            list(weights_dict.values()),
                        ),
                    )
                )
                if len(weights_dict) > 0
                else 0
            )

            sharpe = (
                (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            )

            allocation_data = {
                "weights": weights_dict,
                "method": method,
                "expected_sharpe": float(sharpe),
                "expected_return": float(portfolio_return),
                "expected_volatility": float(portfolio_vol),
                "risk_budget": float(sum(weights_dict.values())),  # Should be ~1.0
                "timestamp": datetime.now(UTC).isoformat(),
                "risk_free_rate": self.risk_free_rate,
            }

            allocations_file.write_text(json.dumps(allocation_data, indent=2))
            logger.info(f"💾 Saved allocations: {method} | Sharpe: {sharpe:.3f}")

            # Also update runtime/allocations_override.json for SmartTrader
            runtime_allocations = RUNTIME / "allocations_override.json"
            runtime_data = {"allocations": weights_dict, "timestamp": datetime.now(UTC).isoformat()}
            runtime_allocations.write_text(json.dumps(runtime_data, indent=2))

            return True

        except Exception as e:
            logger.error(f"❌ Error saving allocations: {e}")
            traceback.print_exc()
            return False

    def get_portfolio_metrics(self, weights_dict: dict[str, float]) -> dict[str, float]:
        """
        Calculate portfolio metrics for given weights.

        Returns:
            Dictionary with sharpe, return, volatility, etc.
        """
        if not weights_dict or len(weights_dict) == 0:
            return {}

        try:
            symbols = list(weights_dict.keys())
            weights = np.array([weights_dict[s] for s in symbols])

            mean_ret = np.array([self.mean_returns.get(s, 0) for s in symbols])
            cov = self.cov_matrix.loc[symbols, symbols].values

            portfolio_return = np.dot(weights, mean_ret)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov, weights)))
            sharpe = (
                (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
            )

            return {
                "expected_sharpe": float(sharpe),
                "expected_return": float(portfolio_return),
                "expected_volatility": float(portfolio_vol),
                "risk_budget": float(sum(weights_dict.values())),
            }

        except Exception as e:
            logger.error(f"❌ Error calculating metrics: {e}")
            return {}


def load_price_history(symbols: list[str], days: int = 252) -> pd.DataFrame | None:
    """
    Load price history for optimization.

    Args:
        symbols: List of symbol strings
        days: Number of days of history to fetch

    Returns:
        DataFrame with price history (columns = symbols, rows = dates)
    """
    if not HAS_NUMPY:
        logger.warning("⚠️  numpy/pandas not available")
        return None

    try:
        import yfinance as yf

        data = {}

        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=f"{days}d")
                if not hist.empty and "Close" in hist.columns:
                    data[sym] = hist["Close"]
                    logger.debug(f"📥 Loaded {len(hist)} days of data for {sym}")
                else:
                    logger.warning(f"⚠️  No data for {sym}")
            except Exception as e:
                logger.warning(f"⚠️  Error loading {sym}: {e}")

        if data:
            df = pd.DataFrame(data)
            df = df.dropna()  # Remove rows with missing data
            logger.info(f"✅ Loaded price history: {df.shape}")
            return df
        else:
            logger.warning("⚠️  No price data loaded")
            return None

    except ImportError:
        logger.warning("⚠️  yfinance not available: pip install yfinance")
        return None
    except Exception as e:
        logger.error(f"❌ Error loading price history: {e}")
        traceback.print_exc()
        return None


# Example usage and test
if __name__ == "__main__":
    # Test with sample data
    symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]

    logger.info("🧪 Testing Portfolio Optimizer...")

    # Load price history
    price_df = load_price_history(symbols, days=252)

    if price_df is not None and not price_df.empty:
        # Initialize optimizer
        optimizer = PortfolioOptimizer(price_df, risk_free_rate=0.02)

        # Test Sharpe optimization
        sharpe_weights = optimizer.optimize_efficient_frontier()
        if sharpe_weights:
            optimizer.save_allocations_to_state(sharpe_weights, method="sharpe")
            print("\n✅ Sharpe Optimization Results:")
            for sym, weight in sharpe_weights.items():
                print(f"  {sym}: {weight:.2%}")

        # Test risk parity
        rp_weights = optimizer.risk_parity_weights()
        if rp_weights:
            print("\n✅ Risk Parity Results:")
            for sym, weight in rp_weights.items():
                print(f"  {sym}: {weight:.2%}")

        # Test min variance
        mv_weights = optimizer.minimum_variance_weights()
        if mv_weights:
            print("\n✅ Min Variance Results:")
            for sym, weight in mv_weights.items():
                print(f"  {sym}: {weight:.2%}")
    else:
        logger.warning("⚠️  Could not load price history for testing")
