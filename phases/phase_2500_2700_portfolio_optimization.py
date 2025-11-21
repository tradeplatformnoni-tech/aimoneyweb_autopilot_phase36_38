#!/usr/bin/env python3
"""
Phase 2500-2700: Portfolio Optimization - World-Class Implementation
--------------------------------------------------------------------
Modern Portfolio Theory optimizations with strategy manager integration:
- Sharpe Ratio Optimization (efficient frontier)
- Correlation Matrix Analysis (rolling windows)
- Risk Parity Allocation
- Efficient Frontier Calculation
- Dynamic Rebalancing
- Integration with strategy_manager for strategy-level optimization
"""

import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
RUNTIME = ROOT / "runtime"
STATE = ROOT / "state"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

for d in [RUNTIME, STATE, DATA, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "portfolio_optimization.log"
logger = logging.getLogger("portfolio_optimization")
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

ALLOCATIONS_FILE = RUNTIME / "allocations_override.json"
OPTIMIZATION_FILE = RUNTIME / "portfolio_optimization.json"
CORRELATION_FILE = STATE / "correlation_matrix.json"
STRATEGY_ALLOCATIONS_FILE = RUNTIME / "strategy_allocations.json"


def load_current_allocations() -> dict[str, float]:
    """Load current portfolio allocations from multiple sources."""
    # Try strategy allocations first (from strategy_manager)
    if STRATEGY_ALLOCATIONS_FILE.exists():
        try:
            data = json.loads(STRATEGY_ALLOCATIONS_FILE.read_text())
            allocations = data.get("allocations", {})
            if allocations:
                return allocations
        except Exception as e:
            logger.debug(f"Could not load strategy allocations: {e}")

    # Fallback to runtime allocations
    if ALLOCATIONS_FILE.exists():
        try:
            data = json.loads(ALLOCATIONS_FILE.read_text())
            return data.get("allocations", {})
        except Exception as e:
            logger.debug(f"Could not load runtime allocations: {e}")

    # Default allocations
    return {"BTC-USD": 0.25, "ETH-USD": 0.2, "SPY": 0.15, "QQQ": 0.2, "GLD": 0.2}


def load_price_history(symbols: list[str], days: int = 252) -> pd.DataFrame | None:
    """Load price history for correlation/optimization."""
    if not HAS_NUMPY:
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
                logger.debug(f"Error loading {sym}: {e}")

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
    return None


def calculate_correlation_matrix_rolling(
    price_df: pd.DataFrame, window_days: int = 30
) -> dict[str, Any]:
    """Calculate rolling correlation matrix for portfolio."""
    if price_df is None or price_df.empty:
        return {}

    try:
        returns = price_df.pct_change().dropna()

        # Calculate rolling correlation if we have enough data
        if len(returns) >= window_days:
            # Use rolling window for more stable correlations
            rolling_corr = returns.rolling(window=min(window_days, len(returns))).corr()
            # Get most recent correlation matrix
            if not rolling_corr.empty:
                # Extract latest correlations
                latest_idx = rolling_corr.index.get_level_values(0).unique()[-1]
                corr_matrix = rolling_corr.loc[latest_idx].to_dict()
            else:
                # Fallback to full period correlation
                corr_matrix = returns.corr().to_dict()
        else:
            # Use full period if not enough data
            corr_matrix = returns.corr().to_dict()

        # Calculate top correlated pairs
        top_pairs = []
        symbols = list(returns.columns)
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i + 1 :]:
                corr = corr_matrix.get(sym1, {}).get(sym2, 0.0)
                if abs(corr) > 0.1:  # Only significant correlations
                    top_pairs.append({"symbol1": sym1, "symbol2": sym2, "correlation": float(corr)})

        top_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return {
            "correlation_matrix": corr_matrix,
            "top_pairs": top_pairs[:10],
            "window_days": window_days,
            "timestamp": datetime.now(UTC).isoformat(),
            "symbols": symbols,
        }
    except Exception as e:
        logger.error(f"❌ Error calculating correlation: {e}")
        traceback.print_exc()
        return {}


def optimize_portfolio(price_df: pd.DataFrame, method: str = "sharpe") -> dict[str, Any]:
    """
    Optimize portfolio using PortfolioOptimizer.

    Args:
        price_df: DataFrame with price history
        method: Optimization method ("sharpe", "risk_parity", "min_variance")

    Returns:
        Optimization results dictionary
    """
    if not HAS_NUMPY or price_df is None or price_df.empty:
        return {}

    try:
        from analytics.portfolio_optimizer import PortfolioOptimizer

        # Initialize optimizer
        optimizer = PortfolioOptimizer(price_df, risk_free_rate=0.02)

        # Get optimal weights based on method
        if method == "sharpe":
            optimal_weights = optimizer.optimize_efficient_frontier()
            method_name = "sharpe"
        elif method == "risk_parity":
            optimal_weights = optimizer.risk_parity_weights()
            method_name = "risk_parity"
        elif method == "min_variance":
            optimal_weights = optimizer.minimum_variance_weights()
            method_name = "min_variance"
        else:
            optimal_weights = optimizer.optimize_efficient_frontier()
            method_name = "sharpe"

        if not optimal_weights:
            logger.warning("⚠️  No optimal weights computed")
            return {}

        # Get portfolio metrics
        metrics = optimizer.get_portfolio_metrics(optimal_weights)

        # Build optimization result
        result = {
            "allocations": optimal_weights,
            "method": method_name,
            "expected_sharpe": metrics.get("expected_sharpe", 0.0),
            "expected_return": metrics.get("expected_return", 0.0),
            "expected_volatility": metrics.get("expected_volatility", 0.0),
            "risk_budget": metrics.get("risk_budget", 1.0),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(
            f"📈 Portfolio optimized ({method_name}): Sharpe {result['expected_sharpe']:.3f}, Return {result['expected_return']:.2%}, Vol {result['expected_volatility']:.2%}"
        )

        return result

    except ImportError:
        logger.warning("⚠️  PortfolioOptimizer not available, using simplified optimization")
        # Fallback to simplified optimization
        try:
            returns = price_df.pct_change().dropna()
            mean_returns = returns.mean()
            cov_matrix = returns.cov()

            n = len(mean_returns)
            if n == 0:
                return {}

            # Risk parity (inverse volatility)
            volatilities = np.sqrt(np.diag(cov_matrix))
            inv_vol = 1.0 / np.maximum(volatilities, 1e-6)
            weights = inv_vol / inv_vol.sum()

            optimal_weights = {sym: float(weights[i]) for i, sym in enumerate(returns.columns)}

            portfolio_return = np.dot(weights, mean_returns) * 252
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights))) * np.sqrt(
                252
            )
            sharpe = (portfolio_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0

            return {
                "allocations": optimal_weights,
                "method": "risk_parity_fallback",
                "expected_sharpe": float(sharpe),
                "expected_return": float(portfolio_return),
                "expected_volatility": float(portfolio_vol),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.error(f"❌ Error in simplified optimization: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error in fallback optimization: {e}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error optimizing portfolio: {e}")
        traceback.print_exc()
        return {}


def should_rebalance(
    current_allocations: dict[str, float],
    optimal_allocations: dict[str, float],
    threshold: float = 0.05,
) -> bool:
    """Check if portfolio should be rebalanced."""
    if not current_allocations or not optimal_allocations:
        return False

    # Check if any allocation differs by more than threshold
    for symbol in optimal_allocations:
        current = current_allocations.get(symbol, 0.0)
        optimal = optimal_allocations.get(symbol, 0.0)
        if abs(current - optimal) > threshold:
            return True

    return False


def main():
    """Main portfolio optimization loop."""
    logger.info("🚀 Portfolio Optimization (Phase 2500-2700) starting...")

    update_interval = int(
        os.getenv("NEOLIGHT_PORTFOLIO_OPTIMIZATION_INTERVAL", "21600")
    )  # Default 6 hours

    while True:
        try:
            # Load current allocations
            current_allocations = load_current_allocations()
            symbols = list(current_allocations.keys())

            if not symbols:
                logger.warning("⚠️  No symbols to optimize")
                time.sleep(3600)
                continue

            logger.info(
                f"📊 Optimizing portfolio for {len(symbols)} assets: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
            )

            # Load price history
            price_df = load_price_history(symbols, days=252)

            if price_df is not None and not price_df.empty:
                # Calculate correlation matrix with rolling window
                corr_data = calculate_correlation_matrix_rolling(price_df, window_days=30)
                if corr_data:
                    CORRELATION_FILE.write_text(json.dumps(corr_data, indent=2))
                    logger.info(
                        f"✅ Correlation matrix updated: {len(corr_data.get('symbols', []))} symbols, {len(corr_data.get('top_pairs', []))} significant pairs"
                    )

                # Optimize portfolio (try sharpe first, fallback to risk_parity)
                optimization = optimize_portfolio(price_df, method="sharpe")

                if not optimization:
                    # Try risk parity if sharpe fails
                    optimization = optimize_portfolio(price_df, method="risk_parity")

                if optimization and "allocations" in optimization:
                    # Save optimization results
                    OPTIMIZATION_FILE.write_text(json.dumps(optimization, indent=2))

                    logger.info("📊 Optimal allocations:")
                    for sym, weight in sorted(
                        optimization["allocations"].items(), key=lambda x: x[1], reverse=True
                    ):
                        logger.info(f"  {sym}: {weight:.2%}")

                    logger.info(f"📈 Expected Sharpe: {optimization.get('expected_sharpe', 0):.3f}")
                    logger.info(f"📈 Expected Return: {optimization.get('expected_return', 0):.2%}")
                    logger.info(
                        f"📉 Expected Volatility: {optimization.get('expected_volatility', 0):.2%}"
                    )

                    # Check if rebalancing is needed
                    if should_rebalance(
                        current_allocations, optimization["allocations"], threshold=0.05
                    ):
                        logger.info("🔄 Rebalancing recommended (allocation difference > 5%)")
                        # Optionally auto-update allocations (for now, just log)
                        # Could integrate with strategy_manager here
                    else:
                        logger.info("✅ Portfolio allocations are optimal (within 5% threshold)")
            else:
                logger.warning("⚠️  Could not load price history for optimization")

            logger.info(
                f"✅ Portfolio optimization complete. Next run in {update_interval / 3600:.1f} hours"
            )
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Portfolio Optimization stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in portfolio optimization loop: {e}")
            traceback.print_exc()
            time.sleep(3600)  # Wait 1 hour before retrying


if __name__ == "__main__":
    main()
