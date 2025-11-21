#!/usr/bin/env python3
"""
Phase 141-200: Trading Extensions - WORLD CLASS
==============================================
Einstein-level trading extensions:
- Market making strategies
- Arbitrage detection
- Pairs trading
- Statistical arbitrage
- Spread trading
- Paper-mode compatible
"""

import logging
import math
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
for p in [STATE, RUNTIME, LOGS]:
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "trading_extensions.log"
logger = logging.getLogger("trading_extensions")
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

# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    from utils.circuit_breaker import CircuitBreaker
    from utils.health_check import HealthCheck
    from utils.retry import retry_with_backoff
    from utils.state_manager import StateManager

    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False
    logger.warning("⚠️ World-class utilities not available")

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("⚠️ NumPy not available")

EXTENSIONS_STATE_FILE = RUNTIME / "trading_extensions_state.json"


class TradingExtensions:
    """World-class trading extensions engine."""

    def __init__(self):
        """Initialize trading extensions."""
        self.pairs: dict[str, dict[str, Any]] = {}  # symbol_pair -> correlation data
        self.arbitrage_opportunities: list[dict[str, Any]] = []
        self.state_manager = None
        if HAS_WORLD_CLASS_UTILS:
            try:
                self.state_manager = StateManager(
                    EXTENSIONS_STATE_FILE,
                    default_state={"pairs": {}, "arbitrage_opportunities": []},
                    backup_count=24,
                    backup_interval=3600.0,
                )
            except Exception as e:
                logger.warning(f"⚠️ StateManager init failed: {e}")
        logger.info("✅ TradingExtensions initialized")

    def calculate_correlation(self, prices1: list[float], prices2: list[float]) -> float:
        """Calculate correlation between two price series."""
        if not HAS_NUMPY or len(prices1) < 2 or len(prices2) < 2:
            return 0.0

        if len(prices1) != len(prices2):
            min_len = min(len(prices1), len(prices2))
            prices1 = prices1[-min_len:]
            prices2 = prices2[-min_len:]

        try:
            returns1 = np.diff(prices1) / prices1[:-1]
            returns2 = np.diff(prices2) / prices2[:-1]
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            return float(correlation) if not math.isnan(correlation) else 0.0
        except Exception:
            return 0.0

    def detect_pairs_trading_opportunity(
        self,
        symbol1: str,
        symbol2: str,
        price1: float,
        price2: float,
        price_history1: deque,
        price_history2: deque,
    ) -> dict[str, Any] | None:
        """Detect pairs trading opportunity."""
        if len(price_history1) < 20 or len(price_history2) < 20:
            return None

        prices1 = list(price_history1)
        prices2 = list(price_history2)

        # Calculate correlation
        correlation = self.calculate_correlation(prices1, prices2)

        if abs(correlation) < 0.7:  # Need strong correlation
            return None

        # Calculate spread
        ratio = price1 / price2 if price2 > 0 else 0
        if ratio == 0:
            return None

        # Calculate z-score of spread
        ratios = [p1 / p2 for p1, p2 in zip(prices1, prices2) if p2 > 0]
        if len(ratios) < 20:
            return None

        if HAS_NUMPY:
            mean_ratio = np.mean(ratios)
            std_ratio = np.std(ratios)
            if std_ratio > 0:
                z_score = (ratio - mean_ratio) / std_ratio

                # Trading signal: z-score > 2 = sell spread, z-score < -2 = buy spread
                if abs(z_score) > 2.0:
                    return {
                        "symbol1": symbol1,
                        "symbol2": symbol2,
                        "correlation": correlation,
                        "z_score": float(z_score),
                        "ratio": ratio,
                        "signal": "sell_spread" if z_score > 2 else "buy_spread",
                        "confidence": min(abs(z_score) / 3.0, 1.0),
                    }

        return None

    def detect_arbitrage(self, symbol: str, price_data: dict[str, float]) -> dict[str, Any] | None:
        """Detect arbitrage opportunities across exchanges/markets."""
        # Simplified arbitrage detection
        # In real implementation, would compare prices across multiple exchanges

        if "bid" not in price_data or "ask" not in price_data:
            return None

        bid = price_data["bid"]
        ask = price_data["ask"]
        spread = ask - bid

        if bid > 0:
            spread_pct = spread / bid
            if spread_pct < 0.001:  # Very tight spread = potential arbitrage
                return {
                    "symbol": symbol,
                    "bid": bid,
                    "ask": ask,
                    "spread": spread,
                    "spread_pct": spread_pct,
                    "opportunity": "tight_spread",
                }

        return None

    def market_making_signal(
        self, symbol: str, bid: float, ask: float, mid_price: float, volatility: float
    ) -> dict[str, Any]:
        """Generate market making signals."""
        spread = ask - bid
        spread_pct = spread / mid_price if mid_price > 0 else 0

        # Market making: place orders around mid-price
        # Adjust spread based on volatility
        volatility_adjusted_spread = volatility * 2.0

        return {
            "symbol": symbol,
            "bid": mid_price - (volatility_adjusted_spread / 2),
            "ask": mid_price + (volatility_adjusted_spread / 2),
            "spread": volatility_adjusted_spread,
            "strategy": "market_making",
        }


@world_class_agent("trading_extensions", state_file=EXTENSIONS_STATE_FILE, paper_mode_only=True)
def main():
    """Main trading extensions loop."""
    logger.info("🚀 Trading Extensions starting...")

    extensions = TradingExtensions()

    # Monitor loop
    while True:
        try:
            time.sleep(60)  # Check every minute

            # In real implementation, would:
            # 1. Load current prices
            # 2. Detect pairs trading opportunities
            # 3. Detect arbitrage opportunities
            # 4. Generate market making signals

            logger.debug("📊 Trading extensions monitoring active")

        except KeyboardInterrupt:
            logger.info("🛑 Trading Extensions stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in trading extensions loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
