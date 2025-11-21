#!/usr/bin/env python3
"""
Phase 3300-3500: Kelly Criterion & Position Sizing - World-Class Implementation
--------------------------------------------------------------------------------
Optimal position sizing using Kelly Criterion with SmartTrader integration:
- Kelly Criterion Calculator (from analytics/kelly_sizing.py)
- Fractional Kelly (0.25x, 0.5x for safety)
- Dynamic Position Sizing based on Edge
- Portfolio Heat Tracking (total risk exposure)
- Maximum Drawdown Position Limits
- Integration with SmartTrader for real-time position sizing
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

LOG_FILE = LOGS / "kelly_sizing.log"
logger = logging.getLogger("kelly_sizing")
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

KELLY_FILE = STATE / "kelly_position_sizing.json"
BRAIN_FILE = RUNTIME / "atlas_brain.json"
PORTFOLIO_FILE = RUNTIME / "portfolio.json"
PNL_HISTORY_FILE = STATE / "pnl_history.csv"
STRATEGY_PERFORMANCE_FILE = STATE / "strategy_performance.json"
PERF_METRICS_FILE = STATE / "performance_metrics.csv"


class KellyPositionSizer:
    """Kelly Criterion position sizing with portfolio heat tracking."""

    def __init__(self, fractional_kelly: float = 0.5, max_position_size: float = 0.15):
        """
        Initialize Kelly position sizer.

        Args:
            fractional_kelly: Fraction of full Kelly to use (0.5 = half Kelly, safer)
            max_position_size: Maximum position size as fraction of equity (0.15 = 15%)
        """
        self.fractional_kelly = fractional_kelly
        self.max_position_size = max_position_size
        logger.info(
            f"✅ KellyPositionSizer initialized (fractional: {fractional_kelly:.0%}, max: {max_position_size:.0%})"
        )

    def load_current_equity(self) -> float:
        """Load current portfolio equity."""
        try:
            if PORTFOLIO_FILE.exists():
                data = json.loads(PORTFOLIO_FILE.read_text())
                equity = data.get("equity")
                if equity:
                    return float(equity)
        except Exception:
            pass

        try:
            if BRAIN_FILE.exists():
                data = json.loads(BRAIN_FILE.read_text())
                equity = data.get("current_equity")
                if equity:
                    return float(equity)
        except Exception:
            pass

        try:
            if PERF_METRICS_FILE.exists() and HAS_NUMPY:
                df = pd.read_csv(PERF_METRICS_FILE)
                if not df.empty and "equity" in df.columns:
                    return float(df["equity"].iloc[-1])
        except Exception:
            pass

        return 100000.0  # Default

    def load_trade_history(self) -> list[dict[str, Any]]:
        """Load trade history from pnl_history.csv."""
        trades = []

        if not PNL_HISTORY_FILE.exists():
            return trades

        try:
            if HAS_NUMPY:
                df = pd.read_csv(PNL_HISTORY_FILE)
                if not df.empty:
                    for _, row in df.iterrows():
                        try:
                            pnl = float(row.get("fee", 0))  # Using fee as proxy for PnL
                            # Try to get actual PnL if available
                            if "pnl" in row and pd.notna(row["pnl"]):
                                pnl = float(row["pnl"])

                            trades.append(
                                {
                                    "symbol": str(row.get("symbol", "UNKNOWN")),
                                    "side": str(row.get("side", "buy")),
                                    "qty": float(row.get("qty", 0)),
                                    "price": float(row.get("price", 0)),
                                    "pnl": pnl,
                                    "timestamp": str(row.get("timestamp", "")),
                                }
                            )
                        except Exception:
                            continue
        except Exception as e:
            logger.debug(f"Error loading trade history: {e}")

        return trades

    def calculate_strategy_performance(
        self, symbol: str, trades: list[dict[str, Any]]
    ) -> dict[str, float]:
        """
        Calculate win rate and reward-risk ratio for a symbol/strategy.

        Args:
            symbol: Symbol to analyze
            trades: List of trades

        Returns:
            Dictionary with win_rate and reward_risk_ratio
        """
        symbol_trades = [t for t in trades if t.get("symbol") == symbol]

        if len(symbol_trades) < 5:
            # Not enough data, return defaults
            return {"win_rate": 0.5, "reward_risk_ratio": 1.0, "trade_count": len(symbol_trades)}

        wins = []
        losses = []

        for trade in symbol_trades:
            pnl = trade.get("pnl", 0.0)
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))

        trade_count = len(symbol_trades)

        if len(wins) + len(losses) == 0:
            win_rate = 0.5
            reward_risk_ratio = 1.0
        else:
            win_rate = len(wins) / (len(wins) + len(losses))

            if len(wins) > 0 and len(losses) > 0:
                avg_win = sum(wins) / len(wins)
                avg_loss = sum(losses) / len(losses)
                reward_risk_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
            elif len(wins) > 0:
                avg_win = sum(wins) / len(wins)
                reward_risk_ratio = avg_win / 0.01  # Estimate
            else:
                reward_risk_ratio = 1.0

        return {
            "win_rate": float(win_rate),
            "reward_risk_ratio": float(reward_risk_ratio),
            "trade_count": trade_count,
            "wins": len(wins),
            "losses": len(losses),
        }

    def calculate_kelly_for_symbol(self, symbol: str, perf: dict[str, float]) -> dict[str, Any]:
        """
        Calculate Kelly position size for a symbol.

        Args:
            symbol: Symbol name
            perf: Performance metrics (win_rate, reward_risk_ratio)

        Returns:
            Kelly sizing information
        """
        try:
            from analytics.kelly_sizing import (
                apply_fractional_kelly,
                calculate_kelly_fraction,
                calculate_position_size,
            )

            win_rate = perf.get("win_rate", 0.5)
            reward_risk_ratio = perf.get("reward_risk_ratio", 1.0)

            # Calculate full Kelly
            full_kelly = calculate_kelly_fraction(win_rate, reward_risk_ratio)

            # Apply fractional Kelly
            fractional_kelly_frac = apply_fractional_kelly(
                win_rate, reward_risk_ratio, fraction=self.fractional_kelly
            )

            # Calculate position size (assuming 2% stop loss)
            equity = self.load_current_equity()
            position_info = calculate_position_size(
                equity=equity,
                win_rate=win_rate,
                reward_risk_ratio=reward_risk_ratio,
                stop_loss_distance=0.02,  # 2% stop loss
                kelly_fraction=self.fractional_kelly,
                max_risk_per_trade=0.01,  # 1% max risk per trade
            )

            # Apply max position size limit
            position_fraction = min(position_info["position_fraction"], self.max_position_size)

            return {
                "symbol": symbol,
                "full_kelly": float(full_kelly),
                "fractional_kelly": float(fractional_kelly_frac),
                "position_fraction": float(position_fraction),
                "position_size": float(equity * position_fraction),
                "win_rate": float(win_rate),
                "reward_risk_ratio": float(reward_risk_ratio),
                "trade_count": perf.get("trade_count", 0),
                "max_position_size": self.max_position_size,
            }

        except ImportError:
            logger.warning("⚠️  kelly_sizing module not available, using simplified calculation")
            # Fallback calculation
            win_rate = perf.get("win_rate", 0.5)
            reward_risk_ratio = perf.get("reward_risk_ratio", 1.0)

            # Simplified Kelly: f = (p * b - q) / b
            q = 1.0 - win_rate
            full_kelly = (
                (win_rate * reward_risk_ratio - q) / reward_risk_ratio
                if reward_risk_ratio > 0
                else 0.0
            )
            full_kelly = max(0.0, min(full_kelly, 0.25))
            fractional_kelly_frac = full_kelly * self.fractional_kelly

            equity = self.load_current_equity()
            position_fraction = min(fractional_kelly_frac, self.max_position_size)

            return {
                "symbol": symbol,
                "full_kelly": float(full_kelly),
                "fractional_kelly": float(fractional_kelly_frac),
                "position_fraction": float(position_fraction),
                "position_size": float(equity * position_fraction),
                "win_rate": float(win_rate),
                "reward_risk_ratio": float(reward_risk_ratio),
                "trade_count": perf.get("trade_count", 0),
                "max_position_size": self.max_position_size,
            }
        except Exception as e:
            logger.error(f"❌ Error calculating Kelly for {symbol}: {e}")
            return {}

    def calculate_portfolio_heat(self, positions: dict[str, float], equity: float) -> float:
        """
        Calculate portfolio heat (total risk exposure).
        Portfolio heat = sum of all position values / equity

        Args:
            positions: Dictionary of {symbol: position_value}
            equity: Total equity

        Returns:
            Portfolio heat as decimal (e.g., 0.5 = 50% of equity at risk)
        """
        if equity <= 0:
            return 0.0

        total_position_value = sum(abs(v) for v in positions.values())
        heat = total_position_value / equity

        return float(heat)

    def load_portfolio_positions(self) -> dict[str, float]:
        """Load current portfolio positions."""
        try:
            if PORTFOLIO_FILE.exists():
                data = json.loads(PORTFOLIO_FILE.read_text())
                positions = data.get("positions", {})
                # Convert to position values
                result = {}
                for symbol, pos_data in positions.items():
                    if isinstance(pos_data, dict):
                        qty = float(pos_data.get("qty", 0))
                        price = float(pos_data.get("avg_price", 0))
                        result[symbol] = qty * price
                    else:
                        result[symbol] = float(pos_data)
                return result
        except Exception as e:
            logger.debug(f"Could not load positions: {e}")
        return {}

    def generate_kelly_report(self) -> dict[str, Any]:
        """Generate comprehensive Kelly position sizing report."""
        try:
            equity = self.load_current_equity()
            trades = self.load_trade_history()

            # Get symbols from allocations
            allocations_file = RUNTIME / "allocations_override.json"
            symbols = []
            if allocations_file.exists():
                try:
                    data = json.loads(allocations_file.read_text())
                    symbols = list(data.get("allocations", {}).keys())
                except Exception:
                    pass

            if not symbols:
                symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]

            # Calculate Kelly for each symbol
            kelly_fractions = {}
            kelly_details = {}

            for symbol in symbols:
                perf = self.calculate_strategy_performance(symbol, trades)
                kelly_info = self.calculate_kelly_for_symbol(symbol, perf)

                if kelly_info:
                    kelly_fractions[symbol] = kelly_info["position_fraction"]
                    kelly_details[symbol] = kelly_info

            # Calculate portfolio heat
            positions = self.load_portfolio_positions()
            portfolio_heat = self.calculate_portfolio_heat(positions, equity)

            # Load drawdown info for max position limits
            max_drawdown = 0.0
            try:
                if PERF_METRICS_FILE.exists() and HAS_NUMPY:
                    df = pd.read_csv(PERF_METRICS_FILE)
                    if not df.empty:
                        equity_series = df["equity"].values if "equity" in df.columns else []
                        if len(equity_series) > 0:
                            peaks = np.maximum.accumulate(equity_series)
                            drawdowns = (peaks - equity_series) / peaks
                            max_drawdown = float(np.max(drawdowns))
            except Exception:
                pass

            # Adjust max position size based on drawdown
            adjusted_max_size = self.max_position_size
            if max_drawdown > 0.15:  # > 15% drawdown
                adjusted_max_size *= 0.5  # Reduce max position size by 50%
            elif max_drawdown > 0.10:  # > 10% drawdown
                adjusted_max_size *= 0.75

            report = {
                "timestamp": datetime.now(UTC).isoformat(),
                "equity": equity,
                "fractional_kelly": self.fractional_kelly,
                "max_position_size": self.max_position_size,
                "adjusted_max_position_size": adjusted_max_size,
                "kelly_fractions": kelly_fractions,
                "kelly_details": kelly_details,
                "portfolio_heat": portfolio_heat,
                "max_drawdown": max_drawdown,
                "positions": positions,
                "total_position_value": sum(positions.values()) if positions else 0.0,
            }

            logger.info(
                f"✅ Kelly report generated: {len(kelly_fractions)} symbols, portfolio heat: {portfolio_heat:.2%}"
            )

            return report

        except Exception as e:
            logger.error(f"❌ Error generating Kelly report: {e}")
            traceback.print_exc()
            return {"timestamp": datetime.now(UTC).isoformat(), "error": str(e)}


def main():
    """Main Kelly sizing loop."""
    logger.info("🚀 Kelly Criterion Position Sizing (Phase 3300-3500) starting...")

    fractional_kelly = float(os.getenv("NEOLIGHT_FRACTIONAL_KELLY", "0.5"))  # Default half Kelly
    max_position_size = float(os.getenv("NEOLIGHT_MAX_POSITION_SIZE", "0.15"))  # Default 15%

    kelly_sizer = KellyPositionSizer(
        fractional_kelly=fractional_kelly, max_position_size=max_position_size
    )

    update_interval = int(os.getenv("NEOLIGHT_KELLY_SIZING_INTERVAL", "3600"))  # Default 1 hour

    while True:
        try:
            # Generate Kelly report
            report = kelly_sizer.generate_kelly_report()

            if "error" not in report:
                # Save Kelly calculations
                KELLY_FILE.write_text(json.dumps(report, indent=2))

                # Log summary
                logger.info("📊 Kelly Position Sizing Summary:")
                logger.info(f"  Portfolio Heat: {report.get('portfolio_heat', 0):.2%}")
                logger.info(f"  Max Drawdown: {report.get('max_drawdown', 0):.2%}")
                logger.info(
                    f"  Adjusted Max Position Size: {report.get('adjusted_max_position_size', 0):.2%}"
                )

                kelly_fractions = report.get("kelly_fractions", {})
                if kelly_fractions:
                    top_symbols = sorted(kelly_fractions.items(), key=lambda x: x[1], reverse=True)[
                        :5
                    ]
                    logger.info("  Top Kelly Allocations:")
                    for symbol, fraction in top_symbols:
                        logger.info(f"    {symbol}: {fraction:.2%}")
            else:
                logger.warning(f"⚠️  Kelly report generation failed: {report.get('error')}")

            logger.info(f"✅ Kelly sizing complete. Next run in {update_interval / 3600:.1f} hours")
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Kelly Criterion Position Sizing stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in Kelly sizing loop: {e}")
            traceback.print_exc()
            time.sleep(600)  # Wait 10 minutes before retrying


if __name__ == "__main__":
    main()
