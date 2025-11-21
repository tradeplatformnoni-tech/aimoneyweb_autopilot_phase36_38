#!/usr/bin/env python3
"""
Risk Attribution Analysis - Phase 4300-4500 Enhancement
========================================================
Calculates risk contribution by strategy, identifies concentrated exposures,
and monitors strategy correlation over time.
"""

import json
import logging
import os
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

LOG_FILE = LOGS / "risk_attribution.log"
logger = logging.getLogger("risk_attribution")
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

RISK_ATTRIBUTION_FILE = STATE / "risk_attribution.json"


class RiskAttributionAnalyzer:
    """
    Analyzes risk contribution by strategy and identifies concentrated exposures.
    """

    def __init__(self):
        """Initialize risk attribution analyzer."""
        self.strategy_performance_file = STATE / "strategy_performance.json"
        self.strategy_allocations_file = RUNTIME / "strategy_allocations.json"
        self.correlation_file = STATE / "correlation_matrix.json"
        logger.info("✅ RiskAttributionAnalyzer initialized")

    def load_strategy_data(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load strategy performance and allocation data."""
        performance_data = {}
        allocation_data = {}

        # Load performance data
        if self.strategy_performance_file.exists():
            try:
                perf_data = json.loads(self.strategy_performance_file.read_text())
                performance_data = perf_data.get("strategy_performance", {})
            except Exception as e:
                logger.warning(f"⚠️  Error loading performance data: {e}")

        # Load allocation data
        if self.strategy_allocations_file.exists():
            try:
                alloc_data = json.loads(self.strategy_allocations_file.read_text())
                allocation_data = alloc_data.get("allocations", {})
            except Exception as e:
                logger.warning(f"⚠️  Error loading allocation data: {e}")

        return performance_data, allocation_data

    def load_correlation_matrix(self) -> dict[str, dict[str, float]]:
        """Load strategy correlation matrix."""
        if self.correlation_file.exists():
            try:
                corr_data = json.loads(self.correlation_file.read_text())
                return corr_data.get("matrix", {})
            except Exception as e:
                logger.warning(f"⚠️  Error loading correlation matrix: {e}")

        return {}

    def calculate_strategy_volatility(
        self, performance_data: dict[str, Any], lookback_days: int = 30
    ) -> dict[str, float]:
        """Calculate volatility for each strategy."""
        strategy_vol = {}

        for strategy_name, perf in performance_data.items():
            # Estimate volatility from performance metrics
            sharpe = perf.get("sharpe_ratio", 0.0)
            max_drawdown = perf.get("max_drawdown", 0.0)
            total_pnl = perf.get("total_pnl", 0.0)
            trade_count = perf.get("trade_count", 0)

            if trade_count > 0:
                # Estimate volatility from drawdown (simplified)
                # Volatility ≈ max_drawdown / 2 (rough estimate)
                volatility = abs(max_drawdown) / 2.0 if max_drawdown != 0 else 0.15

                # Alternative: estimate from Sharpe (assuming 15% annual vol)
                if sharpe > 0:
                    annual_vol = 0.15  # Base assumption
                    volatility = annual_vol / np.sqrt(252)  # Daily vol

                strategy_vol[strategy_name] = max(0.01, min(volatility, 1.0))  # Cap at 100%
            else:
                # Default volatility for strategies with no data
                strategy_vol[strategy_name] = 0.15  # 15% annual default

        return strategy_vol

    def calculate_risk_contribution(
        self,
        allocations: dict[str, float],
        volatilities: dict[str, float],
        correlation_matrix: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """
        Calculate risk contribution for each strategy using portfolio risk decomposition.
        Risk Contribution = weight_i * (Σ * w)_i / portfolio_volatility
        """
        if not allocations or not volatilities:
            return {}

        try:
            strategy_names = list(allocations.keys())
            n = len(strategy_names)

            # Build covariance matrix from volatilities and correlations
            # Cov(i,j) = vol_i * vol_j * corr(i,j)
            cov_matrix = np.zeros((n, n))

            for i, strat1 in enumerate(strategy_names):
                vol1 = volatilities.get(strat1, 0.15)
                for j, strat2 in enumerate(strategy_names):
                    vol2 = volatilities.get(strat2, 0.15)

                    if i == j:
                        # Diagonal: variance = vol^2
                        cov_matrix[i, j] = vol1**2
                    else:
                        # Off-diagonal: use correlation
                        corr = correlation_matrix.get(strat1, {}).get(strat2, 0.0)
                        cov_matrix[i, j] = vol1 * vol2 * corr

            # Portfolio weights vector
            weights = np.array([allocations.get(name, 0.0) for name in strategy_names])

            # Portfolio variance = w^T * Σ * w
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            portfolio_volatility = np.sqrt(max(portfolio_variance, 1e-10))

            # Risk contribution = w_i * (Σ * w)_i / portfolio_volatility
            cov_times_weights = np.dot(cov_matrix, weights)
            risk_contributions = {}

            for i, strategy_name in enumerate(strategy_names):
                risk_contrib = weights[i] * cov_times_weights[i] / portfolio_volatility
                risk_contributions[strategy_name] = float(risk_contrib)

            # Normalize to percentages
            total_risk = sum(risk_contributions.values())
            if total_risk > 0:
                risk_contributions = {
                    k: (v / total_risk) * 100.0 for k, v in risk_contributions.items()
                }

            return risk_contributions

        except Exception as e:
            logger.error(f"❌ Error calculating risk contribution: {e}")
            traceback.print_exc()
            # Fallback: proportional to allocations
            total_alloc = sum(allocations.values())
            if total_alloc > 0:
                return {k: (v / total_alloc) * 100.0 for k, v in allocations.items()}
            return {}

    def identify_concentrated_exposures(
        self,
        allocations: dict[str, float],
        risk_contributions: dict[str, float],
        threshold: float = 40.0,
    ) -> list[dict[str, Any]]:
        """Identify strategies with concentrated risk exposure."""
        concentrated = []

        for strategy_name in allocations:
            allocation = allocations.get(strategy_name, 0.0) * 100.0
            risk_contrib = risk_contributions.get(strategy_name, 0.0)

            # Flag if allocation or risk contribution exceeds threshold
            if allocation > threshold or risk_contrib > threshold:
                concentrated.append(
                    {
                        "strategy": strategy_name,
                        "allocation_pct": allocation,
                        "risk_contribution_pct": risk_contrib,
                        "risk_concentration": risk_contrib / allocation if allocation > 0 else 0.0,
                        "alert": "HIGH_CONCENTRATION",
                    }
                )

        return sorted(concentrated, key=lambda x: x["risk_contribution_pct"], reverse=True)

    def calculate_diversification_score(
        self, allocations: dict[str, float], correlation_matrix: dict[str, dict[str, float]]
    ) -> float:
        """
        Calculate portfolio diversification score.
        Higher score = better diversification (lower correlation, more strategies).
        """
        if not allocations or len(allocations) < 2:
            return 0.0

        try:
            strategy_names = list(allocations.keys())
            n = len(strategy_names)

            # Calculate average pairwise correlation
            correlations = []
            for i, strat1 in enumerate(strategy_names):
                for strat2 in strategy_names[i + 1 :]:
                    corr = correlation_matrix.get(strat1, {}).get(strat2, 0.0)
                    correlations.append(abs(corr))

            avg_correlation = np.mean(correlations) if correlations else 0.0

            # Diversification score: (1 - avg_corr) * number_of_strategies / max_strategies
            # Normalized to 0-100
            max_strategies = 8  # Expected max number of strategies
            strategy_factor = min(n / max_strategies, 1.0)
            diversification_score = (1.0 - avg_correlation) * strategy_factor * 100.0

            return max(0.0, min(100.0, diversification_score))

        except Exception as e:
            logger.error(f"❌ Error calculating diversification score: {e}")
            return 50.0  # Default medium diversification

    def generate_risk_attribution_report(self) -> dict[str, Any]:
        """Generate comprehensive risk attribution report."""
        try:
            # Load data
            performance_data, allocations = self.load_strategy_data()
            correlation_matrix = self.load_correlation_matrix()

            if not allocations:
                logger.warning("⚠️  No allocation data available")
                return {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": "No allocation data available",
                }

            # Calculate volatilities
            volatilities = self.calculate_strategy_volatility(performance_data)

            # Calculate risk contributions
            risk_contributions = self.calculate_risk_contribution(
                allocations, volatilities, correlation_matrix
            )

            # Identify concentrated exposures
            concentrated = self.identify_concentrated_exposures(
                allocations, risk_contributions, threshold=40.0
            )

            # Calculate diversification score
            diversification_score = self.calculate_diversification_score(
                allocations, correlation_matrix
            )

            # Build report
            report = {
                "timestamp": datetime.now(UTC).isoformat(),
                "allocations": {k: v * 100.0 for k, v in allocations.items()},
                "risk_contributions": risk_contributions,
                "volatilities": {k: v * 100.0 for k, v in volatilities.items()},
                "concentrated_exposures": concentrated,
                "diversification_score": diversification_score,
                "portfolio_risk_metrics": {
                    "total_strategies": len(allocations),
                    "average_allocation": np.mean(list(allocations.values())) * 100.0,
                    "max_allocation": max(allocations.values()) * 100.0,
                    "max_risk_contribution": max(risk_contributions.values())
                    if risk_contributions
                    else 0.0,
                    "concentration_alerts": len(concentrated),
                },
            }

            # Save report
            RISK_ATTRIBUTION_FILE.write_text(json.dumps(report, indent=2))
            logger.info(
                f"✅ Risk attribution report generated: {len(allocations)} strategies analyzed"
            )

            return report

        except Exception as e:
            logger.error(f"❌ Error generating risk attribution report: {e}")
            traceback.print_exc()
            return {"timestamp": datetime.now(UTC).isoformat(), "error": str(e)}

    def log_summary(self, report: dict[str, Any]):
        """Log summary of risk attribution."""
        if "error" in report:
            logger.warning(f"⚠️  Risk attribution failed: {report['error']}")
            return

        logger.info("📊 Risk Attribution Summary:")
        logger.info(f"  Diversification Score: {report.get('diversification_score', 0):.1f}/100")
        logger.info(f"  Concentration Alerts: {len(report.get('concentrated_exposures', []))}")

        risk_contrib = report.get("risk_contributions", {})
        if risk_contrib:
            top_risk = max(risk_contrib.items(), key=lambda x: x[1])
            logger.info(f"  Top Risk Contributor: {top_risk[0]} ({top_risk[1]:.1f}%)")

        concentrated = report.get("concentrated_exposures", [])
        if concentrated:
            logger.warning("  ⚠️  Concentrated Exposures:")
            for exp in concentrated[:3]:
                logger.warning(
                    f"    - {exp['strategy']}: {exp['risk_contribution_pct']:.1f}% risk, {exp['allocation_pct']:.1f}% allocation"
                )


def main():
    """Main risk attribution loop."""
    logger.info("🚀 Risk Attribution Analyzer starting...")

    analyzer = RiskAttributionAnalyzer()
    update_interval = int(
        os.getenv("NEOLIGHT_RISK_ATTRIBUTION_INTERVAL", "300")
    )  # Default 5 minutes

    while True:
        try:
            # Generate comprehensive report
            report = analyzer.generate_risk_attribution_report()

            # Log summary
            analyzer.log_summary(report)

            logger.info("✅ Risk attribution complete. Waiting for next cycle...")
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Risk Attribution Analyzer stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in risk attribution loop: {e}")
            traceback.print_exc()
            time.sleep(60)  # Wait 1 minute before retrying


if __name__ == "__main__":
    import time

    main()
