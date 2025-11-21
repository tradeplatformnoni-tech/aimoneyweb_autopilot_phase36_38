#!/usr/bin/env python3
"""
NeoLight RL Trainer - Phase 3700-3900
======================================
Training orchestrator for RL agent.
Loads historical trades, trains offline, saves checkpoints.
Non-intrusive: runs as background process, doesn't affect active trading.
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
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np

from ai.rl_agent import PPOAgent
from ai.rl_environment import TradingEnvironment

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "rl_trainer.log"
logger = logging.getLogger("rl_trainer")
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

# Training configuration
TRAINING_LOG = STATE / "rl_training_log.json"
MIN_TRADES_FOR_TRAINING = 50
TRAINING_WINDOW_SIZE = 1000
RETRAIN_INTERVAL_HOURS = 168  # Weekly
VALIDATION_SPLIT = 0.2


class RLTrainer:
    """
    RL training orchestrator.
    Trains agent on historical data, manages checkpoints, handles retraining.
    """

    def __init__(
        self,
        state_size: int = 34,
        action_size: int = 8,
        retrain_interval_hours: int = RETRAIN_INTERVAL_HOURS,
        min_trades: int = MIN_TRADES_FOR_TRAINING,
    ):
        """
        Initialize trainer.

        Args:
            state_size: Size of state vector
            action_size: Number of strategies
            retrain_interval_hours: Hours between retraining
            min_trades: Minimum trades needed before training
        """
        self.state_size = state_size
        self.action_size = action_size
        self.retrain_interval_hours = retrain_interval_hours
        self.min_trades = min_trades

        # Initialize components
        self.env = TradingEnvironment()
        self.agent = PPOAgent(state_size=state_size, action_size=action_size)

        # Training state
        self.last_training_time: datetime | None = None
        self.training_history: list[dict[str, Any]] = []

        logger.info(
            f"✅ RLTrainer initialized (min_trades={min_trades}, retrain_interval={retrain_interval_hours}h)"
        )

    def _compute_episode_reward(self, trades_df) -> tuple[float, dict[str, float]]:
        """
        Compute a normalized reward for a bundle of trades.

        Args:
            trades_df: DataFrame slice containing trades for an episode

        Returns:
            Tuple of (normalized_reward, debug_metrics)
        """
        metrics: dict[str, float] = {}
        realized_pnl = 0.0
        notional = 0.0
        per_symbol_positions: dict[str, dict[str, float]] = {}

        if trades_df is None or len(trades_df) == 0:
            return 0.0, metrics

        try:
            import pandas as pd

            trades = trades_df.copy()
            # Ensure chronological order when timestamps exist
            if "timestamp" in trades.columns:
                trades = trades.sort_values("timestamp")
            elif "ts" in trades.columns:
                trades = trades.sort_values("ts")

            for row in trades.itertuples(index=False):
                symbol = getattr(row, "symbol", None)
                side = str(getattr(row, "side", "")).lower()
                qty = float(getattr(row, "qty", 0.0) or 0.0)
                price = float(getattr(row, "price", 0.0) or 0.0)

                if not symbol or qty <= 0 or price <= 0:
                    continue

                notional += qty * price

                position = per_symbol_positions.setdefault(symbol, {"qty": 0.0, "avg_price": 0.0})

                if side.startswith("buy"):
                    total_cost = position["avg_price"] * position["qty"] + price * qty
                    position["qty"] += qty
                    if position["qty"] > 0:
                        position["avg_price"] = total_cost / position["qty"]
                elif side.startswith("sell"):
                    sell_qty = min(qty, position["qty"]) if position["qty"] > 0 else qty
                    if sell_qty > 0 and position["qty"] > 0:
                        realized_pnl += (price - position["avg_price"]) * sell_qty
                        position["qty"] -= sell_qty
                    else:
                        # Short sale scenario – treat as flat entry
                        realized_pnl += qty * price * 0.001
                elif side.startswith("close"):
                    if position["qty"] > 0:
                        realized_pnl += (price - position["avg_price"]) * position["qty"]
                        position["qty"] = 0.0
                else:
                    continue

            metrics["realized_pnl"] = realized_pnl
            metrics["notional"] = notional

            if notional <= 0:
                normalized_reward = 0.0
            else:
                normalized_reward = realized_pnl / max(notional, 1.0)

            # Fallback if realized PnL is zero – use simple momentum proxy
            if abs(normalized_reward) < 1e-6:
                momentum_reward = 0.0
                grouped = trades.groupby("symbol")
                for symbol, group in grouped:
                    prices = pd.to_numeric(group["price"], errors="coerce").dropna()
                    if len(prices) >= 2:
                        direction = 1.0
                        buys = (group["side"].str.lower().str.startswith("buy")).sum()
                        sells = (group["side"].str.lower().str.startswith("sell")).sum()
                        if sells > buys:
                            direction = -1.0
                        change = (prices.iloc[-1] - prices.iloc[0]) / max(prices.iloc[0], 1e-6)
                        momentum_reward += direction * change
                if len(grouped) > 0:
                    normalized_reward = momentum_reward / max(len(grouped), 1)
                    metrics["momentum_reward"] = normalized_reward

            if normalized_reward == 0.0 and len(trades) > 0:
                # Small activity bonus to avoid zero rewards
                normalized_reward = min(0.01, len(trades) / 10000.0)
                metrics["activity_reward"] = normalized_reward

            # Clip to keep rewards stable
            normalized_reward = float(np.clip(normalized_reward, -1.0, 1.0))
            metrics["final_reward"] = normalized_reward
            return normalized_reward, metrics

        except Exception as exc:
            logger.debug(f"Reward computation error: {exc}")
            return 0.0, metrics

    def count_recent_trades(self, days: int = 30) -> int:
        """Count trades in recent period."""
        pnl_csv = STATE / "pnl_history.csv"
        if not pnl_csv.exists():
            return 0

        try:
            import pandas as pd

            df = pd.read_csv(pnl_csv)
            if "ts" in df.columns:
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
                df = df.dropna(subset=["ts"])
                if len(df) > 0:
                    cutoff = df["ts"].max() - timedelta(days=days)
                    recent = df[df["ts"] >= cutoff]
                    return len(recent)
            return len(df)
        except Exception as e:
            logger.warning(f"Failed to count trades: {e}")
            return 0

    def should_retrain(self) -> bool:
        """Check if retraining is needed."""
        # Check if enough trades
        trade_count = self.count_recent_trades()
        if trade_count < self.min_trades:
            logger.info(f"Not enough trades for training: {trade_count} < {self.min_trades}")
            return False

        # Check time since last training
        if self.last_training_time is None:
            return True

        time_since = datetime.now(UTC) - self.last_training_time
        hours_since = time_since.total_seconds() / 3600

        if hours_since >= self.retrain_interval_hours:
            logger.info(
                f"Retrain interval reached: {hours_since:.1f}h >= {self.retrain_interval_hours}h"
            )
            return True

        logger.info(
            f"Not time for retraining yet: {hours_since:.1f}h < {self.retrain_interval_hours}h"
        )
        return False

    def load_training_data(
        self, max_trades: int = TRAINING_WINDOW_SIZE
    ) -> list[tuple[np.ndarray, np.ndarray, float]]:
        """
        Load historical trades and convert to training data.

        Returns:
            List of (state, action, reward) tuples
        """
        training_data = []

        try:
            import pandas as pd

            # Load P&L history
            pnl_csv = STATE / "pnl_history.csv"
            if not pnl_csv.exists():
                logger.warning("No P&L history found")
                return training_data

            df = pd.read_csv(pnl_csv)
            if len(df) == 0:
                return training_data

            # Sort by timestamp - handle multiple possible column names
            date_col = None
            if "ts" in df.columns:
                date_col = "ts"
            elif "timestamp" in df.columns:
                date_col = "timestamp"
            elif "date" in df.columns:
                date_col = "date"

            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df.dropna(subset=[date_col]).sort_values(date_col)

            # Limit to recent trades
            if len(df) > max_trades:
                df = df.tail(max_trades)

            logger.info(f"Loading {len(df)} trades for training")

            # Group trades by time windows (daily episodes)
            if date_col:
                df["date"] = df[date_col].dt.date
                dates = df["date"].unique()
                logger.info(f"Found {len(dates)} unique dates for training episodes")
            else:
                # If no date column, group by every N trades
                dates = [None]
                logger.warning("No date column found - using single episode")

            segments: list[tuple[str, Any]] = []

            if date_col:
                # Use more dates for training (up to 100 days or all available)
                # Sort dates to ensure we get the most recent ones
                dates_sorted = sorted(dates) if len(dates) > 0 else []
                max_dates = min(100, len(dates_sorted))
                selected_dates = dates_sorted[-max_dates:] if len(dates_sorted) > 0 else []
                logger.info(
                    f"Processing {len(selected_dates)} dates for training episodes: {selected_dates}"
                )

                for date in selected_dates:
                    day_trades = df[df["date"] == date]
                    if len(day_trades) == 0:
                        continue
                    segments.append((f"day_{date}", day_trades))

            # Add trade-count based segments for entries missing dates (common after ingestion bugs)
            if date_col:
                remainder = df[df["date"].isna()]
            else:
                remainder = df

            if len(remainder) > 0:
                target_chunks = min(75, max(5, len(remainder) // 250))
                chunk_size = max(50, len(remainder) // max(target_chunks, 1))
                chunk_index = 0
                for start in range(0, len(remainder), chunk_size):
                    chunk = remainder.iloc[start : start + chunk_size]
                    if len(chunk) == 0:
                        continue
                    segments.append((f"chunk_{chunk_index}", chunk))
                    chunk_index += 1
                    if len(segments) >= 100:
                        break
                logger.info(
                    f"Added {chunk_index} supplemental chunks for trades lacking date metadata"
                )

            episode_count = 0
            for segment_label, segment_df in segments:
                try:
                    if segment_df is None or len(segment_df) == 0:
                        continue

                    state = self.env.get_state()
                    state_vec = self.env.get_state_vector(state)
                    action = np.ones(self.action_size) / self.action_size

                    reward, reward_metrics = self._compute_episode_reward(segment_df)
                    training_data.append((state_vec, action, reward))
                    episode_count += 1
                    logger.info(
                        f"Created training episode '{segment_label}': reward={reward:.6f}, trades={len(segment_df)}, "
                        f"metrics={reward_metrics}"
                    )
                except Exception as e:
                    logger.warning(f"Error processing training segment {segment_label}: {e}")
                    import traceback

                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    continue

            logger.info(
                f"Successfully created {episode_count} training episodes across {len(segments)} segments"
            )
            logger.info(f"Loaded {len(training_data)} training episodes")

        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            import traceback

            traceback.print_exc()

        return training_data

    def train_episode(self, state: np.ndarray, max_steps: int = 100) -> dict[str, float]:
        """
        Train on a single episode.

        Args:
            state: Initial state
            max_steps: Maximum steps per episode

        Returns:
            Episode metrics
        """
        episode_reward = 0.0
        steps = 0
        previous_state = None

        for step in range(max_steps):
            # Select action
            action, log_prob, value = self.agent.select_action(state)

            # Step environment
            new_state, reward, done, info = self.env.step(action, previous_state)

            # Store transition
            self.agent.store_transition(
                state=state, action=action, reward=reward, log_prob=log_prob, value=value, done=done
            )

            episode_reward += reward
            steps += 1

            if done:
                break

            previous_state = state
            state = self.env.get_state_vector(new_state)

        # Train agent on collected transitions
        if len(self.agent.states) > 0:
            metrics = self.agent.train(epochs=5, batch_size=32)
            metrics["episode_reward"] = episode_reward
            metrics["steps"] = steps
            return metrics

        return {"episode_reward": episode_reward, "steps": steps}

    def train(self, num_episodes: int = 100) -> dict[str, Any]:
        """
        Main training loop.

        Args:
            num_episodes: Number of training episodes

        Returns:
            Training summary
        """
        logger.info(f"🚀 Starting RL training ({num_episodes} episodes)")

        # Load training data
        training_data = self.load_training_data()

        if len(training_data) == 0:
            logger.warning("No training data available")
            return {"status": "no_data", "episodes": 0}

        # Training loop
        total_reward = 0.0
        episode_metrics = []

        for episode in range(min(num_episodes, len(training_data))):
            state_vec, action, reward = training_data[episode]

            # Use historical action or let agent select
            if episode % 2 == 0:  # Alternate between historical and agent actions
                agent_action, log_prob, value = self.agent.select_action(state_vec)
            else:
                agent_action = action
                log_prob = 0.0
                value = 0.0

            # Get new state
            new_state = self.env.get_state()
            new_state_vec = self.env.get_state_vector(new_state)

            # Compute reward
            computed_reward = self.env.compute_reward(None, new_state, agent_action)

            # Store transition
            self.agent.store_transition(
                state=state_vec,
                action=agent_action,
                reward=computed_reward,
                log_prob=log_prob,
                value=value,
                done=False,
            )

            total_reward += computed_reward

            # Train periodically
            if len(self.agent.states) >= 32:
                metrics = self.agent.train(epochs=3, batch_size=32)
                episode_metrics.append(metrics)
                logger.info(
                    f"Episode {episode + 1}/{num_episodes}: reward={computed_reward:.4f}, "
                    f"policy_loss={metrics.get('policy_loss', 0):.4f}"
                )

        # Final training on all collected data
        if len(self.agent.states) > 0:
            final_metrics = self.agent.train(epochs=10, batch_size=64)
            episode_metrics.append(final_metrics)

        # Save checkpoint
        self.agent.save("latest")

        # Update training log
        training_summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "episodes": num_episodes,
            "total_reward": float(total_reward),
            "avg_reward": float(total_reward / num_episodes) if num_episodes > 0 else 0.0,
            "final_metrics": episode_metrics[-1] if episode_metrics else {},
            "training_data_size": len(training_data),
        }

        self.training_history.append(training_summary)
        self.save_training_log()
        self.last_training_time = datetime.now(UTC)

        logger.info(f"✅ Training complete: {training_summary}")
        return training_summary

    def save_training_log(self):
        """Save training history to disk."""
        try:
            log_data = {
                "training_history": self.training_history[-100:],  # Keep last 100 entries
                "last_training": self.last_training_time.isoformat()
                if self.last_training_time
                else None,
                "config": {
                    "state_size": self.state_size,
                    "action_size": self.action_size,
                    "min_trades": self.min_trades,
                    "retrain_interval_hours": self.retrain_interval_hours,
                },
            }
            TRAINING_LOG.write_text(json.dumps(log_data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save training log: {e}")

    def load_training_log(self):
        """Load training history from disk."""
        if TRAINING_LOG.exists():
            try:
                data = json.loads(TRAINING_LOG.read_text())
                self.training_history = data.get("training_history", [])
                last_training_str = data.get("last_training")
                if last_training_str:
                    self.last_training_time = datetime.fromisoformat(
                        last_training_str.replace("Z", "+00:00")
                    )
            except Exception as e:
                logger.warning(f"Failed to load training log: {e}")

    def run_training_loop(self, check_interval_seconds: int = 3600):
        """
        Run continuous training loop (background process).

        Args:
            check_interval_seconds: Seconds between retrain checks
        """
        logger.info("🔄 Starting continuous training loop")
        self.load_training_log()

        # Try to load existing model
        if (STATE / "rl_model" / "checkpoint_latest.pkl").exists():
            self.agent.load("latest")
            logger.info("✅ Loaded existing model")

        while True:
            try:
                if self.should_retrain():
                    logger.info("🔄 Retraining triggered")
                    summary = self.train(num_episodes=50)
                    logger.info(f"✅ Retraining complete: {summary}")
                else:
                    logger.debug("⏸️  Not time for retraining yet")

                time.sleep(check_interval_seconds)

            except KeyboardInterrupt:
                logger.info("Training loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                import traceback

                traceback.print_exc()
                time.sleep(60)  # Wait before retry


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="RL Trainer")
    parser.add_argument("--train", action="store_true", help="Run training")
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes")
    parser.add_argument("--loop", action="store_true", help="Run continuous training loop")
    args = parser.parse_args()

    trainer = RLTrainer()

    if args.loop:
        trainer.run_training_loop()
    elif args.train:
        trainer.train(num_episodes=args.episodes)
    else:
        # Check if retraining needed
        if trainer.should_retrain():
            print("✅ Retraining needed")
            trainer.train()
        else:
            print("⏸️  Not time for retraining")


if __name__ == "__main__":
    main()
