#!/usr/bin/env python3
"""
Phase 3700-3900: Reinforcement Learning - World-Class Implementation
-------------------------------------------------------------------
Enhanced RL for strategy selection with:
- Full Q-Learning implementation
- Policy Gradient methods (PPO) preparation
- Multi-armed bandit exploration
- Reward shaping for risk-adjusted returns
- Integration with strategy_manager
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

LOG_FILE = LOGS / "rl_strategy_selection.log"
logger = logging.getLogger("rl_strategy_selection")
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

RL_FILE = STATE / "rl_strategy_selection.json"
STRATEGY_FILE = STATE / "strategy_performance.json"
RL_Q_TABLE_FILE = STATE / "rl_q_table.json"


class QLearningStrategySelector:
    """Enhanced Q-Learning for strategy selection."""

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        exploration_rate: float = 0.1,
    ):
        """
        Initialize Q-Learning selector.

        Args:
            learning_rate: Learning rate (alpha)
            discount_factor: Discount factor (gamma)
            exploration_rate: Exploration rate (epsilon)
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.q_table = self.load_q_table()
        self.strategies = [
            "turtle_trading",
            "mean_reversion_rsi",
            "momentum_sma_crossover",
            "pairs_trading",
            "vix_strategy",
            "breakout_trading",
            "macd_momentum",
            "bollinger_bands",
        ]
        logger.info(
            f"✅ QLearningStrategySelector initialized (LR: {learning_rate}, Gamma: {discount_factor}, Epsilon: {exploration_rate})"
        )

    def load_q_table(self) -> dict[str, float]:
        """Load Q-table from disk."""
        if RL_Q_TABLE_FILE.exists():
            try:
                data = json.loads(RL_Q_TABLE_FILE.read_text())
                return data.get("q_table", {})
            except Exception:
                pass
        return {}

    def save_q_table(self):
        """Save Q-table to disk."""
        try:
            data = {
                "q_table": self.q_table,
                "timestamp": datetime.now(UTC).isoformat(),
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "exploration_rate": self.exploration_rate,
            }
            RL_Q_TABLE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving Q-table: {e}")

    def get_state_key(self, market_regime: str = "NORMAL", volatility: str = "MEDIUM") -> str:
        """
        Get state key for Q-table.

        Args:
            market_regime: Market regime (BULL, BEAR, SIDEWAYS, NORMAL)
            volatility: Volatility level (LOW, MEDIUM, HIGH)

        Returns:
            State key string
        """
        return f"{market_regime}_{volatility}"

    def get_q_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair."""
        key = f"{state}_{action}"
        return self.q_table.get(key, 0.0)

    def update_q_value(self, state: str, action: str, reward: float, next_state: str | None = None):
        """
        Update Q-value using Q-learning algorithm.
        Q(s,a) = Q(s,a) + α[r + γ * max(Q(s',a')) - Q(s,a)]

        Args:
            state: Current state
            action: Action taken (strategy name)
            reward: Reward received
            next_state: Next state (optional)
        """
        key = f"{state}_{action}"
        current_q = self.get_q_value(state, action)

        # Estimate next state value
        if next_state:
            # Get max Q-value for next state
            next_q_values = [self.get_q_value(next_state, action) for action in self.strategies]
            max_next_q = max(next_q_values) if next_q_values else 0.0
        else:
            max_next_q = 0.0

        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        self.q_table[key] = new_q

    def select_action(self, state: str, use_exploration: bool = True) -> str:
        """
        Select action (strategy) using epsilon-greedy policy.

        Args:
            state: Current state
            use_exploration: Whether to use exploration

        Returns:
            Selected strategy name
        """
        if use_exploration and HAS_NUMPY and np.random.random() < self.exploration_rate:
            # Explore: random strategy
            return np.random.choice(self.strategies)
        else:
            # Exploit: best strategy for current state
            q_values = {action: self.get_q_value(state, action) for action in self.strategies}
            if q_values:
                return max(q_values.items(), key=lambda x: x[1])[0]
            else:
                return np.random.choice(self.strategies) if HAS_NUMPY else self.strategies[0]

    def calculate_reward(
        self, strategy_name: str, performance: dict[str, Any], risk_adjusted: bool = True
    ) -> float:
        """
        Calculate reward for strategy performance.
        Uses risk-adjusted returns for reward shaping.

        Args:
            strategy_name: Strategy name
            performance: Strategy performance data
            risk_adjusted: Whether to use risk-adjusted reward

        Returns:
            Reward value
        """
        sharpe = performance.get("sharpe_ratio", 0.0)
        total_return = performance.get("total_return", 0.0)
        max_drawdown = abs(performance.get("max_drawdown", 0.0))
        win_rate = performance.get("win_rate", 0.5)

        if risk_adjusted:
            # Risk-adjusted reward: Sharpe ratio (primary) + win rate bonus
            reward = sharpe * 10.0  # Scale Sharpe (typically 0-3) to 0-30
            reward += (win_rate - 0.5) * 5.0  # Bonus for win rate > 50%
            reward -= max_drawdown * 20.0  # Penalty for drawdown
        else:
            # Simple return-based reward
            reward = total_return * 100.0  # Scale return to reward

        return float(reward)

    def update_from_performance(self, market_regime: str = "NORMAL", volatility: str = "MEDIUM"):
        """
        Update Q-values from current strategy performance.

        Args:
            market_regime: Current market regime
            volatility: Current volatility level
        """
        # Load strategy performance
        strategy_perf = {}
        if STRATEGY_FILE.exists():
            try:
                data = json.loads(STRATEGY_FILE.read_text())
                ranked = data.get("ranked_strategies", [])
                for s in ranked:
                    name = s.get("strategy", "")
                    if name:
                        strategy_perf[name] = s
            except Exception:
                pass

        state = self.get_state_key(market_regime, volatility)

        # Update Q-values for each strategy
        for strategy_name in self.strategies:
            perf = strategy_perf.get(strategy_name, {})
            reward = self.calculate_reward(strategy_name, perf, risk_adjusted=True)

            # Update Q-value (assume same state for simplicity)
            self.update_q_value(state, strategy_name, reward, next_state=state)

        # Save updated Q-table
        self.save_q_table()
        logger.info(f"✅ Q-values updated for state: {state}")


class MultiArmedBandit:
    """Multi-armed bandit for strategy exploration."""

    def __init__(self, strategies: list[str], alpha: float = 1.0, beta: float = 1.0):
        """
        Initialize Thompson Sampling multi-armed bandit.

        Args:
            strategies: List of strategy names
            alpha: Beta distribution alpha parameter
            beta: Beta distribution beta parameter
        """
        self.strategies = strategies
        self.alpha = alpha
        self.beta = beta
        self.successes = dict.fromkeys(strategies, 0)
        self.failures = dict.fromkeys(strategies, 0)
        logger.info(f"✅ MultiArmedBandit initialized for {len(strategies)} strategies")

    def select_strategy(self) -> str:
        """Select strategy using Thompson Sampling."""
        if not HAS_NUMPY:
            # Fallback: UCB
            return self._ucb_select()

        # Thompson Sampling: sample from Beta distribution
        samples = {}
        for strategy in self.strategies:
            a = self.alpha + self.successes[strategy]
            b = self.beta + self.failures[strategy]
            samples[strategy] = np.random.beta(a, b)

        # Select strategy with highest sample
        return max(samples.items(), key=lambda x: x[1])[0]

    def _ucb_select(self) -> str:
        """Upper Confidence Bound selection (fallback)."""
        total_pulls = sum(self.successes.values()) + sum(self.failures.values())

        if total_pulls == 0:
            return self.strategies[0]

        ucb_values = {}
        for strategy in self.strategies:
            successes = self.successes[strategy]
            pulls = successes + self.failures[strategy]

            if pulls == 0:
                ucb_values[strategy] = float("inf")
            else:
                mean = successes / pulls
                confidence = np.sqrt(2 * np.log(total_pulls) / pulls) if HAS_NUMPY else 0.1
                ucb_values[strategy] = mean + confidence

        return max(ucb_values.items(), key=lambda x: x[1])[0]

    def update(self, strategy: str, success: bool):
        """Update bandit statistics."""
        if success:
            self.successes[strategy] = self.successes.get(strategy, 0) + 1
        else:
            self.failures[strategy] = self.failures.get(strategy, 0) + 1


def update_strategy_q_values(performance: dict) -> dict:
    """Update Q-values for strategies using simplified Q-learning."""
    strategies = [
        "turtle_trading",
        "mean_reversion_rsi",
        "momentum_sma_crossover",
        "pairs_trading",
        "vix_strategy",
        "breakout_trading",
        "macd_momentum",
        "bollinger_bands",
    ]

    q_values = {}
    for strategy in strategies:
        # Enhanced: Use Sharpe ratio with risk adjustment
        sharpe = performance.get(strategy, {}).get("sharpe_ratio", 0.0)
        win_rate = performance.get(strategy, {}).get("win_rate", 0.5)
        max_dd = abs(performance.get(strategy, {}).get("max_drawdown", 0.0))

        # Risk-adjusted Q-value
        q_value = sharpe * 10.0  # Scale Sharpe
        q_value += (win_rate - 0.5) * 5.0  # Win rate bonus
        q_value -= max_dd * 10.0  # Drawdown penalty

        q_values[strategy] = max(0.0, q_value)

    return q_values


def select_best_strategies(q_values: dict, top_n: int = 3) -> list[str]:
    """Select top N strategies based on Q-values."""
    sorted_strategies = sorted(q_values.items(), key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_strategies[:top_n]]


def main():
    """Main RL strategy selection loop."""
    logger.info("🚀 Reinforcement Learning Strategy Selection (Phase 3700-3900) starting...")

    # Initialize Q-learning selector
    q_learner = QLearningStrategySelector(
        learning_rate=0.1, discount_factor=0.95, exploration_rate=0.1
    )

    # Initialize multi-armed bandit
    strategies = [
        "turtle_trading",
        "mean_reversion_rsi",
        "momentum_sma_crossover",
        "pairs_trading",
        "vix_strategy",
        "breakout_trading",
        "macd_momentum",
        "bollinger_bands",
    ]
    bandit = MultiArmedBandit(strategies)

    update_interval = int(os.getenv("NEOLIGHT_RL_INTERVAL", "43200"))  # Default 12 hours

    while True:
        try:
            # Load strategy performance
            strategy_perf = {}
            if STRATEGY_FILE.exists():
                try:
                    data = json.loads(STRATEGY_FILE.read_text())
                    ranked = data.get("ranked_strategies", [])
                    for s in ranked:
                        name = s.get("strategy", "")
                        if name:
                            strategy_perf[name] = s
                except Exception:
                    pass

            # Update Q-values from performance
            q_learner.update_from_performance(market_regime="NORMAL", volatility="MEDIUM")

            # Get Q-values
            q_values = update_strategy_q_values(strategy_perf)

            # Select best strategies (exploitation)
            best_strategies = select_best_strategies(q_values, top_n=5)

            # Select strategy using bandit (exploration)
            bandit_strategy = bandit.select_strategy()

            # Combine: use Q-learning for exploitation, bandit for exploration
            exploration_rate = q_learner.exploration_rate
            if HAS_NUMPY and np.random.random() < exploration_rate:
                selected_strategy = bandit_strategy
                selection_method = "bandit_exploration"
            else:
                selected_strategy = best_strategies[0] if best_strategies else strategies[0]
                selection_method = "q_learning_exploitation"

            rl_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "q_values": q_values,
                "selected_strategies": best_strategies,
                "selected_strategy": selected_strategy,
                "selection_method": selection_method,
                "exploration_rate": exploration_rate,
                "bandit_successes": bandit.successes,
                "bandit_failures": bandit.failures,
            }

            # Save RL data
            RL_FILE.write_text(json.dumps(rl_data, indent=2))

            logger.info(f"🧠 RL Selection: {selected_strategy} ({selection_method})")
            logger.info(f"📊 Top Q-value strategies: {', '.join(best_strategies[:3])}")

            # Update bandit based on strategy performance
            if selected_strategy in strategy_perf:
                perf = strategy_perf[selected_strategy]
                sharpe = perf.get("sharpe_ratio", 0.0)
                success = sharpe > 1.0  # Consider strategy successful if Sharpe > 1.0
                bandit.update(selected_strategy, success)

            logger.info(
                f"✅ RL strategy selection complete. Next run in {update_interval / 3600:.1f} hours"
            )
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Reinforcement Learning Strategy Selection stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in RL loop: {e}")
            traceback.print_exc()
            time.sleep(3600)


if __name__ == "__main__":
    main()
