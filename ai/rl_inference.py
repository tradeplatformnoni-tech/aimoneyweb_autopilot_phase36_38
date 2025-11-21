#!/usr/bin/env python3
"""
NeoLight RL Inference Engine - Phase 3700-3900
===============================================
Live inference engine that generates strategy weights from current market state.
Writes weights to runtime/rl_strategy_weights.json for integration with weights_bridge.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in Python path
_script_dir = Path(__file__).parent.parent.absolute()
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import numpy as np

from ai.rl_agent import PPOAgent
from ai.rl_environment import TradingEnvironment

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "rl_inference.log"
logger = logging.getLogger("rl_inference")
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
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Output file
RL_WEIGHTS_FILE = RUNTIME / "rl_strategy_weights.json"

# Strategy names (must match strategy_research.py and rl_environment.py)
STRATEGIES = [
    "turtle_trading",
    "mean_reversion_rsi",
    "momentum_sma_crossover",
    "breakout_trading",
    "pairs_trading",
    "macd_momentum",
    "bollinger_bands",
    "vix_strategy",
]


class RLInferenceEngine:
    """
    Live inference engine for RL-generated strategy weights.
    Generates weights based on current market state, writes to runtime.
    """

    def __init__(self, state_size: int = 34, action_size: int = 8):
        """
        Initialize inference engine.

        Args:
            state_size: Size of state vector
            action_size: Number of strategies
        """
        self.state_size = state_size
        self.action_size = action_size

        # Initialize components
        self.env = TradingEnvironment()
        self.agent = PPOAgent(state_size=state_size, action_size=action_size)

        # Load model
        self.model_loaded = False
        self.load_model()

        logger.info("✅ RL Inference Engine initialized")

    def load_model(self) -> bool:
        """Load trained model from checkpoint."""
        checkpoint_path = STATE / "rl_model" / "checkpoint_latest.pkl"

        if not checkpoint_path.exists():
            logger.warning("No RL model checkpoint found. Using untrained agent.")
            return False

        try:
            success = self.agent.load("latest")
            if success:
                self.model_loaded = True
                logger.info("✅ Loaded RL model from checkpoint")
            else:
                logger.warning("Failed to load RL model")
            return success
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def generate_weights(self, deterministic: bool = True) -> dict[str, float]:
        """
        Generate strategy weights from current market state.

        Args:
            deterministic: If True, use deterministic policy; if False, sample

        Returns:
            Dictionary mapping strategy names to weights
        """
        try:
            # Get current state
            state = self.env.get_state()
            state_vec = self.env.get_state_vector(state)

            # Generate action (strategy weights)
            action, log_prob, value = self.agent.select_action(
                state_vec, deterministic=deterministic
            )

            # Ensure weights sum to 1.0
            action = action / (np.sum(action) + 1e-8)

            # Map to strategy names
            weights_dict = {}
            for i, strategy_name in enumerate(STRATEGIES):
                if i < len(action):
                    weights_dict[strategy_name] = float(action[i])
                else:
                    weights_dict[strategy_name] = 0.0

            # Normalize to ensure sum = 1.0
            total = sum(weights_dict.values())
            if total > 0:
                weights_dict = {k: v / total for k, v in weights_dict.items()}

            logger.debug(f"Generated weights: {weights_dict}")
            return weights_dict

        except Exception as e:
            logger.error(f"Error generating weights: {e}")
            import traceback

            traceback.print_exc()
            # Fallback to equal weights
            return {s: 1.0 / len(STRATEGIES) for s in STRATEGIES}

    def save_weights(self, weights: dict[str, float], metadata: dict[str, Any] | None = None):
        """
        Save strategy weights to runtime file.

        Args:
            weights: Strategy weights dictionary
            metadata: Optional metadata (timestamp, confidence, etc.)
        """
        try:
            output = {
                "weights": weights,
                "source": "rl_inference",
                "timestamp": datetime.now(UTC).isoformat(),
                "model_loaded": self.model_loaded,
                "metadata": metadata or {},
            }

            RL_WEIGHTS_FILE.write_text(json.dumps(output, indent=2))
            logger.debug(f"✅ Saved RL weights to {RL_WEIGHTS_FILE}")

        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    def update_weights(self, deterministic: bool = True):
        """
        Update strategy weights based on current state.
        Main method called periodically.
        """
        weights = self.generate_weights(deterministic=deterministic)

        metadata = {
            "deterministic": deterministic,
            "sum": sum(weights.values()),
            "top_strategy": max(weights.items(), key=lambda x: x[1])[0] if weights else None,
        }

        self.save_weights(weights, metadata)
        return weights

    def run_inference_loop(self, update_interval_seconds: int = 300):
        """
        Run continuous inference loop (background process).
        Updates weights periodically based on current market state.

        Args:
            update_interval_seconds: Seconds between weight updates
        """
        logger.info(f"🔄 Starting inference loop (update every {update_interval_seconds}s)")

        while True:
            try:
                # Reload model periodically (in case it was retrained)
                if not self.model_loaded or time.time() % 3600 < update_interval_seconds:
                    self.load_model()

                # Update weights
                weights = self.update_weights(deterministic=True)
                top_strategy = max(weights.items(), key=lambda x: x[1])[0] if weights else None
                top_weight = weights.get(top_strategy, 0.0) if top_strategy else 0.0

                logger.info(f"📊 Updated RL weights: top={top_strategy} ({top_weight:.2%})")

                time.sleep(update_interval_seconds)

            except KeyboardInterrupt:
                logger.info("Inference loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in inference loop: {e}")
                import traceback

                traceback.print_exc()
                time.sleep(60)  # Wait before retry


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="RL Inference Engine")
    parser.add_argument("--update", action="store_true", help="Update weights once")
    parser.add_argument("--loop", action="store_true", help="Run continuous inference loop")
    parser.add_argument("--interval", type=int, default=300, help="Update interval (seconds)")
    args = parser.parse_args()

    engine = RLInferenceEngine()

    if args.loop:
        engine.run_inference_loop(update_interval_seconds=args.interval)
    elif args.update:
        weights = engine.update_weights()
        print(f"✅ Updated weights: {weights}")
    else:
        # Default: update once
        weights = engine.update_weights()
        print(f"✅ Generated weights: {weights}")


if __name__ == "__main__":
    main()
