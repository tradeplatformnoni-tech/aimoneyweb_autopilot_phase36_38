#!/usr/bin/env python3
"""
NeoLight Black-Litterman Optimizer - Advanced Math
==================================================
Bayesian portfolio optimization combining market equilibrium with investor views.
More stable than pure Markowitz optimization.
"""

import logging
import os
import traceback
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

LOG_FILE = LOGS / "black_litterman.log"
logger = logging.getLogger("black_litterman")
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


class BlackLittermanOptimizer:
    """
    Black-Litterman portfolio optimization.
    Combines market equilibrium (CAPM) with investor views.
    Formula: w = [(τΣ)^-1 + P'Ω^-1P]^-1 * [(τΣ)^-1Π + P'Ω^-1Q]
    """

    def __init__(self, returns_df: pd.DataFrame, risk_free_rate: float = 0.02, tau: float = 0.05):
        """
        Initialize Black-Litterman optimizer.

        Args:
            returns_df: DataFrame with asset returns
            risk_free_rate: Risk-free rate
            tau: Scaling factor (typically 0.05-0.1)
        """
        if not HAS_PANDAS:
            raise ImportError("pandas required for Black-Litterman optimization")

        self.returns_df = returns_df
        self.risk_free_rate = risk_free_rate
        self.tau = tau

        # Calculate market equilibrium
        self.cov_matrix = self.returns_df.pct_change().dropna().cov() * 252  # Annualized
        self.mean_returns = self.returns_df.mean() * 252  # Annualized

        logger.info(f"✅ BlackLittermanOptimizer initialized for {len(returns_df.columns)} assets")

    def calculate_market_equilibrium(
        self, market_caps: dict[str, float] | None = None
    ) -> np.ndarray:
        """
        Calculate market equilibrium returns (Π) using CAPM.
        If market caps provided, use them; otherwise use equal weights.
        """
        n = len(self.returns_df.columns)

        if market_caps:
            # Use market cap weights
            total_cap = sum(market_caps.values())
            weights = np.array(
                [market_caps.get(col, 0) / total_cap for col in self.returns_df.columns]
            )
        else:
            # Equal weights (market portfolio proxy)
            weights = np.ones(n) / n

        # Market portfolio return
        market_return = np.dot(weights, self.mean_returns.values)

        # Equilibrium returns: Π = δ * Σ * w_market
        # where δ is risk aversion (typically 3-4)
        risk_aversion = 3.0
        pi = risk_aversion * self.cov_matrix.values.dot(weights)

        return pi

    def optimize(
        self, views: dict[str, float] | None = None, view_confidence: dict[str, float] | None = None
    ) -> dict[str, float]:
        """
        Optimize portfolio with Black-Litterman model.

        Args:
            views: Dict of {asset: expected_return} for investor views
            view_confidence: Dict of {asset: confidence} (lower = more confident)

        Returns:
            Optimal weights
        """
        try:
            n = len(self.returns_df.columns)
            asset_names = list(self.returns_df.columns)

            # Market equilibrium returns
            pi = self.calculate_market_equilibrium()

            # If no views, return market equilibrium weights
            if not views:
                # Use inverse optimization to get market weights
                inv_cov = np.linalg.pinv(self.cov_matrix.values)
                excess_returns = pi - self.risk_free_rate
                numerator = inv_cov.dot(excess_returns)
                denominator = np.ones(n).dot(inv_cov).dot(excess_returns)

                if abs(denominator) > 1e-10:
                    weights = numerator / denominator
                    weights = np.clip(weights, 0, 1)
                    weights /= np.sum(weights)
                    return dict(zip(asset_names, weights))

            # Build view matrices
            k = len(views)  # Number of views
            P = np.zeros((k, n))  # View matrix
            Q = np.zeros(k)  # Expected returns from views
            Omega = np.eye(k)  # Uncertainty matrix

            for i, (asset, expected_return) in enumerate(views.items()):
                if asset in asset_names:
                    asset_idx = asset_names.index(asset)
                    P[i, asset_idx] = 1.0
                    Q[i] = expected_return

                    # Set confidence (lower = more confident)
                    if view_confidence and asset in view_confidence:
                        Omega[i, i] = view_confidence[asset]
                    else:
                        Omega[i, i] = 0.5  # Default confidence

            # Black-Litterman formula
            # μ_BL = [(τΣ)^-1 + P'Ω^-1P]^-1 * [(τΣ)^-1Π + P'Ω^-1Q]
            tau_sigma = self.tau * self.cov_matrix.values
            inv_tau_sigma = np.linalg.pinv(tau_sigma)
            inv_omega = np.linalg.pinv(Omega)

            # Combine matrices
            M = inv_tau_sigma + P.T.dot(inv_omega).dot(P)
            inv_M = np.linalg.pinv(M)

            # Expected returns
            mu_bl = inv_M.dot(inv_tau_sigma.dot(pi) + P.T.dot(inv_omega).dot(Q))

            # Optimize weights using mean-variance
            excess_returns = mu_bl - self.risk_free_rate
            numerator = inv_tau_sigma.dot(excess_returns)
            denominator = np.ones(n).dot(inv_tau_sigma).dot(excess_returns)

            if abs(denominator) > 1e-10:
                weights = numerator / denominator
                weights = np.clip(weights, 0, 1)
                weights /= np.sum(weights)

                optimal_weights = dict(zip(asset_names, weights))

                # Calculate portfolio metrics
                portfolio_return = np.dot(weights, mu_bl)
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(self.cov_matrix.values, weights)))
                sharpe = (
                    (portfolio_return - self.risk_free_rate) / portfolio_vol
                    if portfolio_vol > 0
                    else 0
                )

                logger.info(
                    f"📈 Black-Litterman Sharpe: {sharpe:.3f} | Return: {portfolio_return:.2%} | Vol: {portfolio_vol:.2%}"
                )

                return optimal_weights
            else:
                logger.warning("⚠️  Black-Litterman optimization unstable, using market equilibrium")
                return self._market_equilibrium_weights(pi)

        except Exception as e:
            logger.error(f"❌ Error in Black-Litterman optimization: {e}")
            traceback.print_exc()
            return {}

    def _market_equilibrium_weights(self, pi: np.ndarray) -> dict[str, float]:
        """Calculate market equilibrium weights."""
        n = len(self.returns_df.columns)
        inv_cov = np.linalg.pinv(self.cov_matrix.values)
        excess_returns = pi - self.risk_free_rate
        numerator = inv_cov.dot(excess_returns)
        denominator = np.ones(n).dot(inv_cov).dot(excess_returns)

        if abs(denominator) > 1e-10:
            weights = numerator / denominator
            weights = np.clip(weights, 0, 1)
            weights /= np.sum(weights)
            return dict(zip(self.returns_df.columns, weights))

        # Fallback to equal weights
        equal_weight = 1.0 / n
        return dict.fromkeys(self.returns_df.columns, equal_weight)


def main():
    """Test Black-Litterman optimizer."""
    logger.info("🧪 Testing Black-Litterman Optimizer...")

    if not HAS_PANDAS:
        logger.error("❌ pandas required")
        return

    # Example: Create sample returns
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
    np.random.seed(42)
    returns = pd.DataFrame(
        {
            "SPY": np.random.normal(0.0005, 0.01, 252),
            "QQQ": np.random.normal(0.0006, 0.012, 252),
            "GLD": np.random.normal(0.0003, 0.008, 252),
            "BTC-USD": np.random.normal(0.001, 0.02, 252),
        },
        index=dates,
    )

    # Convert to prices
    prices = (1 + returns).cumprod() * 100

    # Initialize optimizer
    optimizer = BlackLittermanOptimizer(prices, risk_free_rate=0.02, tau=0.05)

    # Add views (e.g., BTC will outperform)
    views = {
        "BTC-USD": 0.15  # 15% expected return
    }
    view_confidence = {
        "BTC-USD": 0.3  # Moderate confidence
    }

    # Optimize
    weights = optimizer.optimize(views=views, view_confidence=view_confidence)

    logger.info(f"✅ Optimal weights: {weights}")


if __name__ == "__main__":
    main()
