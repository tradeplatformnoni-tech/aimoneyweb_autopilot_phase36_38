#!/usr/bin/env python3
"""
Cross-Agent Risk Correlation Matrix - World-Class Enhancement
=============================================================
Computes rolling correlation between strategies/symbols with:
- 30-day rolling correlation windows
- Dashboard visualization data
- Correlation-based risk alerts
- Integration with portfolio optimizer
"""

import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE_DIR = ROOT / "state"
RUNTIME_DIR = ROOT / "runtime"
LOGS_DIR = ROOT / "logs"

for d in [STATE_DIR, RUNTIME_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "correlation_matrix.log"
logger = logging.getLogger("correlation_matrix")
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

OUTPUT_FILE = STATE_DIR / "correlation_matrix.json"
PNL_HISTORY_FILE = STATE_DIR / "pnl_history.csv"
STRATEGY_PERFORMANCE_FILE = STATE_DIR / "strategy_performance.json"


class CorrelationMatrix:
    """Enhanced correlation matrix with rolling windows and alerts."""

    def __init__(self, window_days: int = 30):
        """
        Initialize correlation matrix calculator.

        Args:
            window_days: Rolling window size in days
        """
        self.window_days = window_days
        logger.info(f"✅ CorrelationMatrix initialized (window: {window_days} days)")

    def load_returns_data(self) -> pd.DataFrame | None:
        """
            Load returns data from multiple sources.

        Returns:
                DataFrame with returns (columns = symbols/strategies, rows = dates)
        """
        if not HAS_NUMPY:
            return None

        returns_data = {}

        # Method 1: Try to load from pnl_history.csv (symbol-level returns)
        try:
            if PNL_HISTORY_FILE.exists():
                df = pd.read_csv(PNL_HISTORY_FILE)
                if not df.empty:
                    # Group by symbol and calculate daily returns
                    if (
                        "symbol" in df.columns
                        and "price" in df.columns
                        and "timestamp" in df.columns
                    ):
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        df = df.sort_values("timestamp")

                        for symbol in df["symbol"].unique():
                            symbol_df = df[df["symbol"] == symbol].copy()
                            symbol_df = symbol_df.set_index("timestamp")

                            # Calculate returns from price changes
                            symbol_df["returns"] = symbol_df["price"].pct_change()
                            returns_data[symbol] = symbol_df["returns"].dropna()
        except Exception as e:
            logger.debug(f"Error loading returns from pnl_history: {e}")

        # Method 2: Try to load strategy performance data
        try:
            if STRATEGY_PERFORMANCE_FILE.exists():
                perf_data = json.loads(STRATEGY_PERFORMANCE_FILE.read_text())
                strategies = perf_data.get("strategies", {})

                for strategy_name, strategy_data in strategies.items():
                    # Try to extract returns from strategy performance
                    # This would need strategy-level returns data
                    pass
        except Exception as e:
            logger.debug(f"Error loading strategy performance: {e}")

        # Method 3: Fallback - use price history from yfinance
        if not returns_data:
            try:
                import yfinance as yf

                allocations_file = RUNTIME_DIR / "allocations_override.json"
                symbols = []
                if allocations_file.exists():
                    data = json.loads(allocations_file.read_text())
                    symbols = list(data.get("allocations", {}).keys())

                if not symbols:
                    symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]

                for sym in symbols:
                    try:
                        ticker = yf.Ticker(sym)
                        hist = ticker.history(
                            period=f"{self.window_days * 2}d"
                        )  # Get more data for rolling window
                        if not hist.empty and "Close" in hist.columns:
                            returns = hist["Close"].pct_change().dropna()
                            returns_data[sym] = returns
                    except Exception:
                        continue
            except ImportError:
                logger.warning("⚠️  yfinance not available")

        if not returns_data:
            logger.warning("⚠️  No returns data available")
            return None

        # Combine into DataFrame
        try:
            # Align all series by date
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()  # Remove rows with missing data

            if returns_df.empty:
                logger.warning("⚠️  Empty returns DataFrame after alignment")
                return None

            logger.info(
                f"✅ Loaded returns data: {returns_df.shape} (symbols: {len(returns_df.columns)}, days: {len(returns_df)})"
            )
            return returns_df
        except Exception as e:
            logger.error(f"❌ Error creating returns DataFrame: {e}")
            return None

    def compute_rolling_correlation(
        self, returns_df: pd.DataFrame, window_days: int | None = None
    ) -> dict[str, Any]:
        """
        Compute rolling correlation matrix.

        Args:
            returns_df: DataFrame with returns
            window_days: Rolling window size (defaults to self.window_days)

        Returns:
            Correlation matrix data
        """
        if returns_df is None or returns_df.empty:
            return {}

        window = window_days or self.window_days
        window = min(window, len(returns_df))  # Can't be larger than data

        try:
            # Compute full-period correlation
            full_corr = returns_df.corr().fillna(0.0)

            # Compute rolling correlation if we have enough data
            rolling_corr = None
            if len(returns_df) >= window:
                rolling_corr_df = returns_df.rolling(window=window).corr()
                if not rolling_corr_df.empty:
                    # Get most recent correlation matrix
                    latest_date = rolling_corr_df.index.get_level_values(0).unique()[-1]
                    rolling_corr = rolling_corr_df.loc[latest_date].fillna(0.0)

            # Use rolling if available, otherwise use full period
            corr_matrix = rolling_corr if rolling_corr is not None else full_corr

            # Convert to dictionary
            corr_dict = corr_matrix.to_dict()

            # Find top correlated pairs
            top_pairs = []
            symbols = list(returns_df.columns)
            for i, sym1 in enumerate(symbols):
                for sym2 in symbols[i + 1 :]:
                    corr = corr_dict.get(sym1, {}).get(sym2, 0.0)
                    if abs(corr) > 0.1:  # Only significant correlations
                        top_pairs.append(
                            {
                                "symbol1": sym1,
                                "symbol2": sym2,
                                "correlation": float(corr),
                                "abs_correlation": abs(float(corr)),
                            }
                        )

            # Sort by absolute correlation
            top_pairs.sort(key=lambda x: x["abs_correlation"], reverse=True)

            # Calculate average correlation (diversification metric)
            correlations = [pair["correlation"] for pair in top_pairs]
            avg_correlation = np.mean(correlations) if correlations else 0.0

            result = {
                "window": f"{window}d",
                "matrix": corr_dict,
                "top_pairs": top_pairs[:20],  # Top 20 pairs
                "average_correlation": float(avg_correlation),
                "symbols": symbols,
                "data_points": len(returns_df),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"📊 Correlation matrix computed: {len(symbols)} symbols, {len(top_pairs)} significant pairs, avg corr: {avg_correlation:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error computing correlation: {e}")
            traceback.print_exc()
            return {}

    def check_correlation_alerts(self, corr_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Check for correlation-based risk alerts.

        Args:
            corr_data: Correlation matrix data

        Returns:
            List of alerts
        """
        alerts = []

        try:
            avg_correlation = corr_data.get("average_correlation", 0.0)
            top_pairs = corr_data.get("top_pairs", [])

            # Alert if average correlation is too high (low diversification)
            if avg_correlation > 0.7:
                alerts.append(
                    {
                        "type": "high_correlation",
                        "severity": "high",
                        "message": f"High average correlation ({avg_correlation:.2%}) - low portfolio diversification",
                        "recommendation": "Consider diversifying into uncorrelated assets",
                    }
                )

            # Alert on highly correlated pairs
            for pair in top_pairs[:5]:  # Check top 5 pairs
                corr = pair.get("abs_correlation", 0.0)
                if corr > 0.9:
                    alerts.append(
                        {
                            "type": "high_pair_correlation",
                            "severity": "medium",
                            "symbol1": pair.get("symbol1"),
                            "symbol2": pair.get("symbol2"),
                            "correlation": corr,
                            "message": f"Very high correlation between {pair.get('symbol1')} and {pair.get('symbol2')}: {corr:.2%}",
                            "recommendation": "Consider reducing exposure to one of these assets",
                        }
                    )

            logger.info(f"🔔 Correlation alerts: {len(alerts)} alerts generated")

        except Exception as e:
            logger.error(f"❌ Error checking correlation alerts: {e}")

        return alerts

    def generate_correlation_report(self) -> dict[str, Any]:
        """Generate comprehensive correlation report."""
        try:
            # Load returns data
            returns_df = self.load_returns_data()

            if returns_df is None or returns_df.empty:
                return {
                    "error": "No returns data available",
                    "timestamp": datetime.now().isoformat(),
                }

            # Compute correlation matrix
            corr_data = self.compute_rolling_correlation(returns_df)

            if not corr_data:
                return {
                    "error": "Failed to compute correlation matrix",
                    "timestamp": datetime.now().isoformat(),
                }

            # Check for alerts
            alerts = self.check_correlation_alerts(corr_data)

            # Build comprehensive report
            report = {
                **corr_data,
                "alerts": alerts,
                "diversification_score": max(
                    0.0, 1.0 - abs(corr_data.get("average_correlation", 0.0))
                ),  # Higher = better diversification
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"✅ Correlation report generated: {len(corr_data.get('symbols', []))} symbols, {len(alerts)} alerts"
            )

            return report

        except Exception as e:
            logger.error(f"❌ Error generating correlation report: {e}")
            traceback.print_exc()
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


def compute_correlation_matrix(window_days: int = 30) -> dict[str, Any]:
    """
    Compute rolling correlation matrix from agent returns.
    Legacy function for backward compatibility.

    Args:
        window_days: Rolling window in days

    Returns:
        Correlation matrix dict
    """
    correlation_matrix = CorrelationMatrix(window_days=window_days)
    report = correlation_matrix.generate_correlation_report()
    return report


def main():
    """Main correlation computation."""
    logger.info("🚀 Correlation Matrix Computation starting...")

    window_days = int(os.getenv("NEOLIGHT_CORRELATION_WINDOW", "30"))
    update_interval = int(os.getenv("NEOLIGHT_CORRELATION_INTERVAL", "3600"))  # Default 1 hour

    correlation_matrix = CorrelationMatrix(window_days=window_days)

    while True:
        try:
            # Generate correlation report
            report = correlation_matrix.generate_correlation_report()

            if "error" not in report:
                # Save correlation matrix
                OUTPUT_FILE.write_text(json.dumps(report, indent=2))

                # Log summary
                logger.info("📊 Correlation Matrix Summary:")
                logger.info(f"  Symbols: {len(report.get('symbols', []))}")
                logger.info(f"  Average Correlation: {report.get('average_correlation', 0):.3f}")
                logger.info(
                    f"  Diversification Score: {report.get('diversification_score', 0):.3f}"
                )
                logger.info(f"  Alerts: {len(report.get('alerts', []))}")

                # Log top correlated pairs
                top_pairs = report.get("top_pairs", [])[:5]
                if top_pairs:
                    logger.info("  Top Correlated Pairs:")
                    for pair in top_pairs:
                        logger.info(
                            f"    {pair.get('symbol1')} - {pair.get('symbol2')}: {pair.get('correlation', 0):.3f}"
                        )
            else:
                logger.warning(f"⚠️  Correlation report generation failed: {report.get('error')}")

            logger.info(
                f"✅ Correlation computation complete. Next run in {update_interval / 3600:.1f} hours"
            )
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Correlation Matrix Computation stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in correlation computation loop: {e}")
            traceback.print_exc()
            time.sleep(600)  # Wait 10 minutes before retrying


if __name__ == "__main__":
    main()
