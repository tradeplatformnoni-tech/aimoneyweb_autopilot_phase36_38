#!/usr/bin/env python3
"""
NeoLight Advanced Risk Management - Phase 2700–2900
==================================================
World-class risk metrics and stress testing:
- Conditional Value at Risk (CVaR)
- Stress scenario simulation
- Liquidity risk assessment
- Drawdown prediction
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("⚠️  Install numpy and pandas: pip install numpy pandas")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "risk_enhancements.log"
logger = logging.getLogger("risk_enhancements")
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


class AdvancedRiskManager:
    """
    World-class advanced risk management with CVaR, stress testing, and liquidity analysis.
    All metrics use percent-of-equity normalization.
    """

    def __init__(self, returns: np.ndarray):
        """
        Initialize risk manager.

        Args:
            returns: Array of portfolio returns (percentages, e.g., 0.01 = 1%)
        """
        if not HAS_NUMPY:
            raise ImportError("numpy required for risk management")

        self.returns = np.array(returns)
        if len(self.returns) == 0:
            logger.warning("⚠️  Empty returns array")
        logger.info(f"✅ AdvancedRiskManager initialized with {len(self.returns)} observations")

    def calculate_cvar(self, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.

        CVaR is the expected loss given that the loss exceeds VaR.
        More conservative than VaR as it considers tail risk.

        Args:
            confidence: Confidence level (0.95 = 95%, 0.99 = 99%)

        Returns:
            CVaR as a percentage (negative value, e.g., -0.05 = -5%)
        """
        if len(self.returns) == 0:
            logger.warning("⚠️  Cannot calculate CVaR: no data")
            return 0.0

        try:
            sorted_returns = np.sort(self.returns)
            cutoff_index = int((1 - confidence) * len(sorted_returns))

            if cutoff_index == 0:
                cutoff_index = 1  # At least 1 observation

            # Tail losses (worst returns)
            tail_losses = sorted_returns[:cutoff_index]

            if len(tail_losses) == 0:
                logger.warning("⚠️  No tail losses found")
                return 0.0

            cvar = np.mean(tail_losses)

            logger.info(f"⚠️  CVaR({confidence * 100:.0f}%): {cvar:.4f} ({cvar * 100:.2f}%)")
            return float(cvar)

        except Exception as e:
            logger.error(f"❌ Error calculating CVaR: {e}")
            import traceback

            traceback.print_exc()
            return 0.0

    def calculate_var(self, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).

        Args:
            confidence: Confidence level (0.95 = 95%)

        Returns:
            VaR as a percentage (negative value)
        """
        if len(self.returns) == 0:
            return 0.0

        try:
            sorted_returns = np.sort(self.returns)
            cutoff_index = int((1 - confidence) * len(sorted_returns))

            if cutoff_index == 0:
                cutoff_index = 1

            var = sorted_returns[cutoff_index - 1]
            logger.debug(f"📊 VaR({confidence * 100:.0f}%): {var:.4f}")
            return float(var)

        except Exception as e:
            logger.error(f"❌ Error calculating VaR: {e}")
            return 0.0

    def stress_test(self, drop_pct: float = -0.10) -> dict[str, Any]:
        """
        Simulate market crash scenario.

        Args:
            drop_pct: Market drop percentage (e.g., -0.10 = -10%)

        Returns:
            Dictionary with stress test results
        """
        if len(self.returns) == 0:
            logger.warning("⚠️  Cannot stress test: no data")
            return {"status": "ERROR", "message": "No data available"}

        try:
            # Calculate current expected return
            current_return = np.mean(self.returns)

            # Apply stress scenario
            stress_return = current_return + drop_pct

            # Calculate portfolio impact
            # Assuming linear relationship (simplified)
            impact = stress_return - current_return

            # Determine status
            if stress_return < -0.20:  # >20% loss
                status = "CRITICAL"
            elif stress_return < -0.10:  # >10% loss
                status = "SEVERE"
            elif stress_return < -0.05:  # >5% loss
                status = "MODERATE"
            else:
                status = "OK"

            result = {
                "status": status,
                "drop_scenario": drop_pct,
                "current_return": float(current_return),
                "stress_return": float(stress_return),
                "impact": float(impact),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.warning(
                f"💣 Stress scenario ({drop_pct * 100:.1f}% drop): {status} | Expected return: {stress_return:.4f}"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error in stress test: {e}")
            import traceback

            traceback.print_exc()
            return {"status": "ERROR", "message": str(e)}

    def liquidity_risk(self, spreads: list[float], threshold: float = 0.05) -> dict[str, Any]:
        """
        Estimate liquidity risk from average bid-ask spreads.

        Args:
            spreads: List of bid-ask spreads (as percentages, e.g., 0.001 = 0.1%)
            threshold: Maximum acceptable spread (default 5% = 0.05)

        Returns:
            Dictionary with liquidity risk assessment
        """
        if not spreads or len(spreads) == 0:
            logger.warning("⚠️  No spread data for liquidity risk")
            return {"risk_score": 0.5, "status": "UNKNOWN"}

        try:
            spreads_array = np.array(spreads)
            avg_spread = np.mean(spreads_array)
            max_spread = np.max(spreads_array)

            # Liquidity score: 1.0 = perfect, 0.0 = illiquid
            # Normalize by threshold
            liquidity_score = max(0.0, min(1.0, 1.0 - (avg_spread / threshold)))

            # Risk score: inverse of liquidity
            risk_score = 1.0 - liquidity_score

            # Determine status
            if risk_score > 0.7:
                status = "HIGH"
            elif risk_score > 0.4:
                status = "MODERATE"
            else:
                status = "LOW"

            result = {
                "risk_score": float(risk_score),
                "liquidity_score": float(liquidity_score),
                "avg_spread": float(avg_spread),
                "max_spread": float(max_spread),
                "status": status,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info(
                f"💧 Liquidity risk: {status} | Score: {risk_score:.3f} | Avg spread: {avg_spread:.4f}"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error calculating liquidity risk: {e}")
            import traceback

            traceback.print_exc()
            return {"risk_score": 0.5, "status": "ERROR"}

    def calculate_max_drawdown(self) -> dict[str, float]:
        """
        Calculate maximum drawdown from returns series.

        Returns:
            Dictionary with max_drawdown, current_drawdown, etc.
        """
        if len(self.returns) == 0:
            return {"max_drawdown": 0.0, "current_drawdown": 0.0}

        try:
            # Convert returns to cumulative equity curve
            cumulative = np.cumprod(1 + self.returns)

            # Calculate running maximum
            running_max = np.maximum.accumulate(cumulative)

            # Drawdown = (current - peak) / peak
            drawdown = (cumulative - running_max) / running_max

            max_drawdown = np.min(drawdown)  # Most negative
            current_drawdown = drawdown[-1]  # Latest

            result = {
                "max_drawdown": float(max_drawdown),
                "current_drawdown": float(current_drawdown),
                "recovery_ratio": float(-max_drawdown / (current_drawdown + 1e-10))
                if current_drawdown < 0
                else 1.0,
            }

            logger.info(f"📉 Max drawdown: {max_drawdown:.2%} | Current: {current_drawdown:.2%}")
            return result

        except Exception as e:
            logger.error(f"❌ Error calculating drawdown: {e}")
            import traceback

            traceback.print_exc()
            return {"max_drawdown": 0.0, "current_drawdown": 0.0}

    def get_comprehensive_risk_report(self, spreads: list[float] | None = None) -> dict[str, Any]:
        """
        Generate comprehensive risk report with all metrics.

        Args:
            spreads: Optional list of bid-ask spreads for liquidity analysis

        Returns:
            Complete risk assessment dictionary
        """
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "cvar_95": self.calculate_cvar(0.95),
            "cvar_99": self.calculate_cvar(0.99),
            "var_95": self.calculate_var(0.95),
            "var_99": self.calculate_var(0.99),
            "stress_test_5pct": self.stress_test(-0.05),
            "stress_test_10pct": self.stress_test(-0.10),
            "stress_test_20pct": self.stress_test(-0.20),
            "drawdown": self.calculate_max_drawdown(),
        }

        if spreads:
            report["liquidity_risk"] = self.liquidity_risk(spreads)

        return report


# Example usage
if __name__ == "__main__":
    # Test with sample data
    logger.info("🧪 Testing Advanced Risk Manager...")

    # Generate sample returns (realistic trading returns)
    np.random.seed(42)
    sample_returns = np.random.normal(0.001, 0.02, 100)  # Mean 0.1% daily, 2% volatility

    # Initialize risk manager
    risk_mgr = AdvancedRiskManager(sample_returns)

    # Test CVaR
    cvar_95 = risk_mgr.calculate_cvar(0.95)
    cvar_99 = risk_mgr.calculate_cvar(0.99)
    print(f"\n✅ CVaR 95%: {cvar_95:.4f} ({cvar_95 * 100:.2f}%)")
    print(f"✅ CVaR 99%: {cvar_99:.4f} ({cvar_99 * 100:.2f}%)")

    # Test stress scenarios
    stress_5 = risk_mgr.stress_test(-0.05)
    stress_10 = risk_mgr.stress_test(-0.10)
    print(f"\n✅ Stress test (-5%): {stress_5['status']}")
    print(f"✅ Stress test (-10%): {stress_10['status']}")

    # Test liquidity risk
    sample_spreads = [0.001, 0.002, 0.0015, 0.003, 0.002]  # 0.1% to 0.3% spreads
    liquidity = risk_mgr.liquidity_risk(sample_spreads)
    print(f"\n✅ Liquidity risk: {liquidity['status']} | Score: {liquidity['risk_score']:.3f}")

    # Comprehensive report
    report = risk_mgr.get_comprehensive_risk_report(sample_spreads)
    print("\n✅ Comprehensive risk report generated")
