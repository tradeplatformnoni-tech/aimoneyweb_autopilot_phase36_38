#!/usr/bin/env python3
"""
NeoLight Cointegration Analyzer - Advanced Math
===============================================
Find cointegrated pairs for statistical arbitrage (pairs trading).
More robust than correlation - identifies true long-term relationships.
"""

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

try:
    import pandas as pd
    from statsmodels.tsa.stattools import adfuller, coint

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "cointegration_analyzer.log"
logger = logging.getLogger("cointegration_analyzer")
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


class CointegrationAnalyzer:
    """
    Analyzes cointegration between pairs of assets.
    Uses Engle-Granger cointegration test.
    """

    def __init__(self, prices_df: pd.DataFrame):
        """
        Initialize cointegration analyzer.

        Args:
            prices_df: DataFrame with asset prices (columns = assets, rows = time)
        """
        if not HAS_STATSMODELS:
            raise ImportError("statsmodels required for cointegration analysis")

        self.prices_df = prices_df
        self.asset_names = list(prices_df.columns)

        logger.info(f"✅ CointegrationAnalyzer initialized for {len(self.asset_names)} assets")

    def test_cointegration(
        self, asset1: str, asset2: str, significance_level: float = 0.05
    ) -> dict[str, Any]:
        """
        Test cointegration between two assets using Engle-Granger test.

        Args:
            asset1: First asset name
            asset2: Second asset name
            significance_level: Significance level (default 0.05 = 5%)

        Returns:
            Dictionary with test results
        """
        if asset1 not in self.asset_names or asset2 not in self.asset_names:
            return {"cointegrated": False, "error": "Asset not found"}

        try:
            prices1 = self.prices_df[asset1].values
            prices2 = self.prices_df[asset2].values

            # Remove NaN values
            valid_idx = ~(np.isnan(prices1) | np.isnan(prices2))
            prices1 = prices1[valid_idx]
            prices2 = prices2[valid_idx]

            if len(prices1) < 30:
                return {"cointegrated": False, "error": "Insufficient data"}

            # Test cointegration
            score, pvalue, _ = coint(prices1, prices2)

            is_cointegrated = pvalue < significance_level

            # Calculate spread
            spread = prices1 - prices2
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)

            # Z-score
            z_score = (spread[-1] - spread_mean) / spread_std if spread_std > 0 else 0.0

            result = {
                "cointegrated": is_cointegrated,
                "pvalue": float(pvalue),
                "score": float(score),
                "spread_mean": float(spread_mean),
                "spread_std": float(spread_std),
                "current_zscore": float(z_score),
                "significance_level": significance_level,
            }

            if is_cointegrated:
                logger.info(f"✅ {asset1} and {asset2} are cointegrated (p={pvalue:.4f})")
            else:
                logger.debug(f"❌ {asset1} and {asset2} are not cointegrated (p={pvalue:.4f})")

            return result

        except Exception as e:
            logger.error(f"❌ Error testing cointegration: {e}")
            return {"cointegrated": False, "error": str(e)}

    def find_cointegrated_pairs(self, significance_level: float = 0.05) -> list[dict[str, Any]]:
        """
        Find all cointegrated pairs.

        Args:
            significance_level: Significance level

        Returns:
            List of cointegrated pairs with test results
        """
        cointegrated_pairs = []

        n = len(self.asset_names)
        for i in range(n):
            for j in range(i + 1, n):
                asset1 = self.asset_names[i]
                asset2 = self.asset_names[j]

                result = self.test_cointegration(asset1, asset2, significance_level)

                if result.get("cointegrated", False):
                    cointegrated_pairs.append({"asset1": asset1, "asset2": asset2, **result})

        # Sort by p-value (lower = stronger cointegration)
        cointegrated_pairs.sort(key=lambda x: x.get("pvalue", 1.0))

        logger.info(f"✅ Found {len(cointegrated_pairs)} cointegrated pairs")

        return cointegrated_pairs

    def calculate_hedge_ratio(self, asset1: str, asset2: str) -> float:
        """
        Calculate hedge ratio (beta) for pairs trading.
        Uses OLS regression: asset1 = alpha + beta * asset2 + error

        Returns:
            Hedge ratio (beta)
        """
        if asset1 not in self.asset_names or asset2 not in self.asset_names:
            return 1.0

        try:
            prices1 = self.prices_df[asset1].values
            prices2 = self.prices_df[asset2].values

            # Remove NaN
            valid_idx = ~(np.isnan(prices1) | np.isnan(prices2))
            prices1 = prices1[valid_idx]
            prices2 = prices2[valid_idx]

            if len(prices1) < 30:
                return 1.0

            # OLS regression: prices1 = beta * prices2
            # beta = cov(prices1, prices2) / var(prices2)
            cov = np.cov(prices1, prices2)[0, 1]
            var = np.var(prices2)

            hedge_ratio = cov / var if var > 0 else 1.0

            return float(hedge_ratio)

        except Exception as e:
            logger.error(f"❌ Error calculating hedge ratio: {e}")
            return 1.0


def main():
    """Test Cointegration Analyzer."""
    logger.info("🧪 Testing Cointegration Analyzer...")

    if not HAS_STATSMODELS:
        logger.error("❌ statsmodels required")
        return

    # Example: Create cointegrated pair
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
    np.random.seed(42)

    # Create two cointegrated series
    common_trend = np.cumsum(np.random.randn(252) * 0.5)
    prices1 = 100 + common_trend + np.random.randn(252) * 0.5
    prices2 = 50 + common_trend * 0.8 + np.random.randn(252) * 0.5  # Slightly different

    prices_df = pd.DataFrame({"SPY": prices1, "QQQ": prices2}, index=dates)

    # Initialize analyzer
    analyzer = CointegrationAnalyzer(prices_df)

    # Test cointegration
    result = analyzer.test_cointegration("SPY", "QQQ")

    logger.info(f"✅ Cointegration test: {result}")

    # Calculate hedge ratio
    hedge_ratio = analyzer.calculate_hedge_ratio("SPY", "QQQ")
    logger.info(f"✅ Hedge ratio: {hedge_ratio:.4f}")


if __name__ == "__main__":
    main()
