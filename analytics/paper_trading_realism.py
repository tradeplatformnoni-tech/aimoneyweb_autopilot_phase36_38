#!/usr/bin/env python3
"""
Paper Trading Realism Enhancement - World-Class Implementation
==============================================================
Enhances paper trading with realistic market conditions:
- Slippage simulation based on order size and volatility
- Latency modeling (order execution delay)
- Fill simulation (partial fills, rejections)
- Market impact simulation
- Realistic bid-ask spread simulation
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

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "paper_trading_realism.log"
logger = logging.getLogger("paper_trading_realism")
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

REALISM_CONFIG_FILE = STATE / "paper_trading_realism.json"


class PaperTradingRealism:
    """Enhanced paper trading realism simulation."""

    def __init__(self):
        """Initialize realism simulator."""
        self.config = self.load_config()
        logger.info("✅ PaperTradingRealism initialized")

    def load_config(self) -> dict[str, Any]:
        """Load realism configuration."""
        default_config = {
            "slippage_enabled": True,
            "slippage_model": "adaptive",  # "fixed", "adaptive", "volume_based"
            "base_slippage_bps": 5,  # 5 basis points base slippage
            "latency_enabled": True,
            "latency_ms": 50,  # 50ms average latency
            "latency_jitter_ms": 20,  # ±20ms jitter
            "fill_simulation_enabled": True,
            "fill_probability": 0.95,  # 95% fill probability
            "partial_fill_enabled": True,
            "partial_fill_probability": 0.1,  # 10% chance of partial fill
            "market_impact_enabled": True,
            "spread_simulation_enabled": True,
            "base_spread_bps": 2,  # 2 bps base spread
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if REALISM_CONFIG_FILE.exists():
            try:
                saved_config = json.loads(REALISM_CONFIG_FILE.read_text())
                default_config.update(saved_config)
            except Exception:
                pass

        return default_config

    def simulate_slippage(
        self, symbol: str, side: str, quantity: float, target_price: float, volatility: float = 0.02
    ) -> float:
        """
        Simulate slippage for an order.

        Args:
            symbol: Symbol to trade
            side: "buy" or "sell"
            quantity: Order quantity
            target_price: Target execution price
            volatility: Current volatility (default 2%)

        Returns:
            Actual execution price (with slippage)
        """
        if not self.config.get("slippage_enabled", True):
            return target_price

        if not HAS_NUMPY:
            # Simple fixed slippage
            base_slippage = self.config.get("base_slippage_bps", 5) / 10000.0
            return (
                target_price * (1 + base_slippage)
                if side == "buy"
                else target_price * (1 - base_slippage)
            )

        try:
            model = self.config.get("slippage_model", "adaptive")
            base_slippage_bps = self.config.get("base_slippage_bps", 5)

            if model == "adaptive":
                # Adaptive slippage: base + volatility + size impact
                volatility_impact = volatility * 100  # Convert to bps
                size_impact = min(10, quantity * 0.001)  # Size impact (cap at 10 bps)
                total_slippage_bps = base_slippage_bps + volatility_impact + size_impact
            elif model == "volume_based":
                # Volume-based: larger orders = more slippage
                order_value = quantity * target_price
                size_multiplier = min(3.0, 1.0 + (order_value / 10000.0) * 0.1)
                total_slippage_bps = base_slippage_bps * size_multiplier
            else:
                # Fixed slippage
                total_slippage_bps = base_slippage_bps

            # Add random component
            random_component = np.random.normal(0, total_slippage_bps * 0.3)
            total_slippage_bps += random_component
            total_slippage_bps = max(0, min(50, total_slippage_bps))  # Cap at 50 bps

            slippage_pct = total_slippage_bps / 10000.0

            # Apply slippage (buy: pay more, sell: receive less)
            if side == "buy":
                actual_price = target_price * (1 + slippage_pct)
            else:
                actual_price = target_price * (1 - slippage_pct)

            logger.debug(
                f"💰 Slippage simulation: {symbol} {side} {quantity} @ ${target_price:.2f} → ${actual_price:.2f} ({slippage_pct * 10000:.1f} bps)"
            )

            return float(actual_price)

        except Exception as e:
            logger.error(f"❌ Error simulating slippage: {e}")
            return target_price

    def simulate_latency(self) -> float:
        """
        Simulate order execution latency.

        Returns:
            Latency in seconds
        """
        if not self.config.get("latency_enabled", True):
            return 0.0

        try:
            base_latency_ms = self.config.get("latency_ms", 50)
            jitter_ms = self.config.get("latency_jitter_ms", 20)

            if HAS_NUMPY:
                latency_ms = base_latency_ms + np.random.normal(0, jitter_ms)
                latency_ms = max(10, min(200, latency_ms))  # Cap between 10-200ms
            else:
                latency_ms = base_latency_ms

            return latency_ms / 1000.0  # Convert to seconds

        except Exception:
            return 0.05  # Default 50ms

    def simulate_fill(self, symbol: str, side: str, quantity: float) -> dict[str, Any]:
        """
        Simulate order fill (full, partial, or rejection).

        Args:
            symbol: Symbol to trade
            side: "buy" or "sell"
            quantity: Order quantity

        Returns:
            Fill result with {filled: bool, filled_quantity: float, rejected: bool}
        """
        if not self.config.get("fill_simulation_enabled", True):
            return {"filled": True, "filled_quantity": quantity, "rejected": False}

        try:
            fill_probability = self.config.get("fill_probability", 0.95)

            if HAS_NUMPY:
                fill_roll = np.random.random()
            else:
                import random

                fill_roll = random.random()

            if fill_roll > fill_probability:
                # Order rejected
                return {"filled": False, "filled_quantity": 0.0, "rejected": True}

            # Check for partial fill
            if self.config.get("partial_fill_enabled", True):
                partial_prob = self.config.get("partial_fill_probability", 0.1)

                if HAS_NUMPY:
                    partial_roll = np.random.random()
                else:
                    import random

                    partial_roll = random.random()

                if partial_roll < partial_prob:
                    # Partial fill (50-90% of order)
                    fill_ratio = 0.5 + (HAS_NUMPY and np.random.random() * 0.4 or 0.4)
                    filled_qty = quantity * fill_ratio
                    return {"filled": True, "filled_quantity": float(filled_qty), "rejected": False}

            # Full fill
            return {"filled": True, "filled_quantity": float(quantity), "rejected": False}

        except Exception as e:
            logger.error(f"❌ Error simulating fill: {e}")
            return {"filled": True, "filled_quantity": quantity, "rejected": False}

    def simulate_market_impact(
        self, symbol: str, side: str, quantity: float, current_price: float
    ) -> float:
        """
        Simulate market impact of order.

        Args:
            symbol: Symbol to trade
            side: "buy" or "sell"
            quantity: Order quantity
            current_price: Current market price

        Returns:
            Market impact adjustment (price change)
        """
        if not self.config.get("market_impact_enabled", True):
            return 0.0

        try:
            # Market impact: sqrt(order_size / average_daily_volume)
            # Simplified: assume impact scales with order value
            order_value = quantity * current_price

            if order_value < 1000:
                impact_bps = 0.5  # Small order: minimal impact
            elif order_value < 10000:
                impact_bps = 2.0  # Medium order: moderate impact
            else:
                impact_bps = 5.0  # Large order: significant impact

            # Add random component
            if HAS_NUMPY:
                impact_bps += np.random.normal(0, impact_bps * 0.3)

            impact_pct = impact_bps / 10000.0

            # Market impact: buy pushes price up, sell pushes price down
            if side == "buy":
                price_change = current_price * impact_pct
            else:
                price_change = -current_price * impact_pct

            return float(price_change)

        except Exception:
            return 0.0

    def simulate_spread(self, symbol: str, mid_price: float) -> dict[str, float]:
        """
        Simulate bid-ask spread.

        Args:
            symbol: Symbol to trade
            mid_price: Mid price

        Returns:
            Dictionary with {bid: float, ask: float, spread_bps: float}
        """
        if not self.config.get("spread_simulation_enabled", True):
            return {"bid": mid_price, "ask": mid_price, "spread_bps": 0.0}

        try:
            base_spread_bps = self.config.get("base_spread_bps", 2)

            # Add volatility component
            volatility_multiplier = 1.5  # Higher vol = wider spread
            spread_bps = base_spread_bps * volatility_multiplier

            # Add random component
            if HAS_NUMPY:
                spread_bps += np.random.normal(0, spread_bps * 0.2)

            spread_bps = max(1, min(20, spread_bps))  # Cap between 1-20 bps
            spread_pct = spread_bps / 10000.0

            bid = mid_price * (1 - spread_pct / 2)
            ask = mid_price * (1 + spread_pct / 2)

            return {"bid": float(bid), "ask": float(ask), "spread_bps": float(spread_bps)}

        except Exception:
            return {"bid": mid_price, "ask": mid_price, "spread_bps": 0.0}

    def apply_realism(
        self, symbol: str, side: str, quantity: float, target_price: float, volatility: float = 0.02
    ) -> dict[str, Any]:
        """
        Apply all realism simulations to an order.

        Args:
            symbol: Symbol to trade
            side: "buy" or "sell"
            quantity: Order quantity
            target_price: Target execution price
            volatility: Current volatility

        Returns:
            Realistic execution result
        """
        # Simulate latency
        latency = self.simulate_latency()

        # Simulate fill
        fill_result = self.simulate_fill(symbol, side, quantity)

        if fill_result["rejected"]:
            return {
                "executed": False,
                "rejected": True,
                "filled_quantity": 0.0,
                "execution_price": target_price,
                "latency": latency,
                "reason": "Order rejected by market",
            }

        filled_quantity = fill_result["filled_quantity"]

        # Simulate market impact
        market_impact = self.simulate_market_impact(symbol, side, filled_quantity, target_price)
        price_with_impact = target_price + market_impact

        # Simulate slippage
        execution_price = self.simulate_slippage(
            symbol, side, filled_quantity, price_with_impact, volatility
        )

        # Simulate spread
        spread_data = self.simulate_spread(symbol, execution_price)

        return {
            "executed": True,
            "rejected": False,
            "filled_quantity": filled_quantity,
            "execution_price": execution_price,
            "target_price": target_price,
            "slippage": execution_price - target_price,
            "market_impact": market_impact,
            "latency": latency,
            "spread": spread_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def main():
    """Main paper trading realism loop."""
    logger.info("🚀 Paper Trading Realism Enhancement starting...")

    realism = PaperTradingRealism()
    update_interval = int(os.getenv("NEOLIGHT_PAPER_REALISM_INTERVAL", "3600"))  # Default 1 hour

    while True:
        try:
            # Save configuration
            REALISM_CONFIG_FILE.write_text(json.dumps(realism.config, indent=2))

            logger.info("✅ Paper trading realism configured:")
            logger.info(
                f"  Slippage: {'Enabled' if realism.config.get('slippage_enabled') else 'Disabled'}"
            )
            logger.info(
                f"  Latency: {'Enabled' if realism.config.get('latency_enabled') else 'Disabled'}"
            )
            logger.info(
                f"  Fill Simulation: {'Enabled' if realism.config.get('fill_simulation_enabled') else 'Disabled'}"
            )
            logger.info(
                f"  Market Impact: {'Enabled' if realism.config.get('market_impact_enabled') else 'Disabled'}"
            )

            logger.info(
                f"✅ Paper trading realism active. Next run in {update_interval / 3600:.1f} hours"
            )
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Paper Trading Realism Enhancement stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in paper trading realism loop: {e}")
            traceback.print_exc()
            time.sleep(3600)


if __name__ == "__main__":
    main()
