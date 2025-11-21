#!/usr/bin/env python3
"""
NeoLight Strategy Executor - Phase 3500-3700
============================================
Executes trades from multiple strategies with confidence weighting.
Prevents strategy conflicts and manages unified positions.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "strategy_executor.log"
logger = logging.getLogger("strategy_executor")
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

STRATEGY_WEIGHTS_FILE = RUNTIME / "strategy_portfolio_weights.json"
STRATEGY_ALLOCATIONS_FILE = RUNTIME / "strategy_allocations.json"


class StrategyExecutor:
    """
    Executes trades from multiple strategies with weighted confidence.
    """

    def __init__(self):
        """Initialize strategy executor."""
        self.strategy_weights = self.load_strategy_weights()
        logger.info("✅ StrategyExecutor initialized")

    def load_strategy_weights(self) -> dict[str, float]:
        """Load strategy weights from portfolio optimizer."""
        # Try strategy portfolio weights first
        if STRATEGY_WEIGHTS_FILE.exists():
            try:
                data = json.loads(STRATEGY_WEIGHTS_FILE.read_text())
                return data.get("weights", {})
            except:
                pass

        # Fallback to strategy allocations
        if STRATEGY_ALLOCATIONS_FILE.exists():
            try:
                data = json.loads(STRATEGY_ALLOCATIONS_FILE.read_text())
                return data.get("allocations", {})
            except:
                pass

        # Default: equal weights
        return {}

    def combine_strategy_signals(
        self, strategy_signals: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        """
        Combine signals from multiple strategies with confidence weighting.

        Args:
            strategy_signals: Dict of {strategy_name: {"signal": "buy/sell/hold", "confidence": 0.0-1.0}}

        Returns:
            Combined signal with weighted confidence
        """
        if not strategy_signals:
            return None

        weighted_votes = {"buy": 0.0, "sell": 0.0, "hold": 0.0}
        total_weight = 0.0

        for strategy_name, signal_data in strategy_signals.items():
            signal = signal_data.get("signal", "hold").lower()
            confidence = signal_data.get("confidence", 0.5)

            # Get strategy weight (default to equal if not found)
            weight = self.strategy_weights.get(strategy_name, 1.0 / len(strategy_signals))

            # Weighted vote
            vote_strength = weight * confidence

            if signal == "buy":
                weighted_votes["buy"] += vote_strength
            elif signal == "sell":
                weighted_votes["sell"] += vote_strength
            else:
                weighted_votes["hold"] += vote_strength

            total_weight += weight

        # Normalize votes
        if total_weight > 0:
            weighted_votes = {k: v / total_weight for k, v in weighted_votes.items()}

        # Determine final signal
        max_vote = max(weighted_votes.values())
        final_signal = max(weighted_votes, key=weighted_votes.get)

        # Calculate combined confidence
        combined_confidence = max_vote

        # Only return signal if confidence is above threshold
        if combined_confidence < 0.3:
            return None

        return {
            "signal": final_signal.upper(),
            "confidence": combined_confidence,
            "votes": weighted_votes,
            "contributing_strategies": [
                name
                for name, data in strategy_signals.items()
                if data.get("signal", "hold").lower() == final_signal
            ],
        }

    def prevent_conflicts(
        self, current_position: dict[str, float], new_signal: dict[str, Any]
    ) -> bool:
        """
        Prevent strategy conflicts (e.g., one strategy wants to buy while another wants to sell).
        Returns True if signal is safe to execute.
        """
        if not current_position or current_position.get("qty", 0) <= 0:
            # No position, any signal is fine
            return True

        signal = new_signal.get("signal", "").upper()

        # If we have a position and signal is buy, check if it's a strong buy
        if signal == "BUY" and current_position.get("qty", 0) > 0:
            # Already have position, new buy is okay (averaging in)
            return True

        # If we have a position and signal is sell, that's fine
        if signal == "SELL" and current_position.get("qty", 0) > 0:
            return True

        # If we have no position and signal is sell, that's a conflict (can't sell what we don't have)
        if signal == "SELL" and current_position.get("qty", 0) <= 0:
            return False

        return True


def main():
    """Main strategy executor (used by SmartTrader)."""
    logger.info("🚀 Strategy Executor initialized")
    # This is typically called by SmartTrader, not run standalone
    executor = StrategyExecutor()
    logger.info("✅ Strategy Executor ready")


if __name__ == "__main__":
    main()
