#!/usr/bin/env python3
"""
NeoLight Hierarchical Risk Parity (HRP) - Advanced Math
=======================================================
Clustering-based portfolio construction, more robust than risk parity.
Handles non-stationary correlations better than traditional methods.
"""

import logging
import os
import traceback
from pathlib import Path

import numpy as np

try:
    import pandas as pd
    from scipy.cluster.hierarchy import dendrogram, leaves_list, linkage
    from scipy.spatial.distance import squareform

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "hierarchical_risk_parity.log"
logger = logging.getLogger("hierarchical_risk_parity")
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


class HierarchicalRiskParity:
    """
    Hierarchical Risk Parity portfolio optimization.
    Algorithm:
    1. Build correlation matrix
    2. Hierarchical clustering
    3. Quasi-diagonalization
    4. Recursive bisection
    """

    def __init__(self, returns_df: pd.DataFrame):
        """
        Initialize HRP optimizer.

        Args:
            returns_df: DataFrame with asset returns (columns = assets, rows = time)
        """
        if not HAS_SCIPY:
            raise ImportError("scipy required for Hierarchical Risk Parity")

        self.returns_df = returns_df
        self.cov_matrix = returns_df.pct_change().dropna().cov() * 252  # Annualized
        self.corr_matrix = self.cov_matrix.corr()
        self.asset_names = list(returns_df.columns)

        logger.info(f"✅ HierarchicalRiskParity initialized for {len(self.asset_names)} assets")

    def optimize(self) -> dict[str, float]:
        """
        Optimize portfolio using Hierarchical Risk Parity.

        Returns:
            Optimal weights
        """
        try:
            # Step 1: Build distance matrix from correlation
            # Distance = sqrt(0.5 * (1 - correlation))
            corr_values = self.corr_matrix.values
            distance_matrix = np.sqrt(0.5 * (1 - corr_values))

            # Step 2: Hierarchical clustering
            # Convert to condensed distance matrix
            condensed_dist = squareform(distance_matrix, checks=False)
            linkage_matrix = linkage(condensed_dist, method="ward")

            # Step 3: Quasi-diagonalization (reorder by dendrogram)
            leaves = leaves_list(linkage_matrix)
            reordered_corr = corr_values[np.ix_(leaves, leaves)]
            reordered_cov = self.cov_matrix.values[np.ix_(leaves, leaves)]
            reordered_names = [self.asset_names[i] for i in leaves]

            # Step 4: Recursive bisection
            weights = self._recursive_bisection(reordered_cov, len(reordered_names))

            # Map weights back to original asset order
            optimal_weights = {}
            for i, name in enumerate(reordered_names):
                optimal_weights[name] = weights[i]

            # Normalize
            total_weight = sum(optimal_weights.values())
            if total_weight > 0:
                optimal_weights = {k: v / total_weight for k, v in optimal_weights.items()}

            logger.info(f"📊 HRP weights computed for {len(optimal_weights)} assets")

            return optimal_weights

        except Exception as e:
            logger.error(f"❌ Error in HRP optimization: {e}")
            traceback.print_exc()
            # Fallback to equal weights
            equal_weight = 1.0 / len(self.asset_names)
            return dict.fromkeys(self.asset_names, equal_weight)

    def _recursive_bisection(self, cov_matrix: np.ndarray, n: int) -> np.ndarray:
        """
        Recursive bisection algorithm for HRP.
        Splits portfolio into two clusters and allocates risk equally.
        """
        if n == 1:
            return np.array([1.0])

        # Split into two clusters
        mid = n // 2

        # Left cluster
        left_cov = cov_matrix[:mid, :mid]
        left_weights = self._recursive_bisection(left_cov, mid)

        # Right cluster
        right_cov = cov_matrix[mid:, mid:]
        right_weights = self._recursive_bisection(right_cov, n - mid)

        # Calculate cluster variances
        left_var = np.dot(left_weights, np.dot(left_cov, left_weights))
        right_var = np.dot(right_weights, np.dot(right_cov, right_weights))

        # Allocate risk equally between clusters
        if left_var > 0 and right_var > 0:
            # Inverse variance weighting
            left_weight = 1.0 / left_var
            right_weight = 1.0 / right_var
            total_weight = left_weight + right_weight

            if total_weight > 0:
                left_weight /= total_weight
                right_weight /= total_weight
            else:
                left_weight = 0.5
                right_weight = 0.5
        else:
            left_weight = 0.5
            right_weight = 0.5

        # Combine weights
        combined_weights = np.zeros(n)
        combined_weights[:mid] = left_weights * left_weight
        combined_weights[mid:] = right_weights * right_weight

        return combined_weights


def main():
    """Test Hierarchical Risk Parity."""
    logger.info("🧪 Testing Hierarchical Risk Parity...")

    if not HAS_SCIPY:
        logger.error("❌ scipy required")
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
    optimizer = HierarchicalRiskParity(prices)

    # Optimize
    weights = optimizer.optimize()

    logger.info(f"✅ HRP weights: {weights}")


if __name__ == "__main__":
    main()
