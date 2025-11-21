#!/usr/bin/env python3
"""
NeoLight RL Trading Environment - Phase 3700-3900
==================================================
World-class trading environment wrapper for reinforcement learning.
Computes states from market data and portfolio, rewards from trade outcomes.
Non-intrusive: reads-only from SmartTrader, never modifies active trading.
"""

import json
import logging
import os
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  Install pandas: pip install pandas")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "rl_environment.log"
logger = logging.getLogger("rl_environment")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Strategy names (must match strategy_research.py)
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


class State(NamedTuple):
    """RL state representation."""

    market_features: np.ndarray  # Volatility, trend, momentum, volume
    portfolio_features: np.ndarray  # Equity, cash ratio, drawdown, positions
    strategy_performance: np.ndarray  # Recent Sharpe, win rates, P&L per strategy
    market_regime: np.ndarray  # Bull/bear indicators, VIX proxy
    timestamp: str


class TradingEnvironment:
    """
    Trading environment for RL training.
    Computes states from market/portfolio data and rewards from trade outcomes.
    """

    def __init__(
        self,
        lookback_window: int = 30,
        state_size: int = 34,
        reward_sharpe_weight: float = 0.6,
        reward_pnl_weight: float = 0.3,
        reward_drawdown_penalty: float = 0.1,
    ):
        """
        Initialize trading environment.

        Args:
            lookback_window: Days of history to use for state computation
            state_size: Total state vector size
            reward_sharpe_weight: Weight for Sharpe ratio in reward
            reward_pnl_weight: Weight for P&L in reward
            reward_drawdown_penalty: Penalty weight for drawdown
        """
        self.lookback_window = lookback_window
        self.state_size = state_size
        self.reward_sharpe_weight = reward_sharpe_weight
        self.reward_pnl_weight = reward_pnl_weight
        self.reward_drawdown_penalty = reward_drawdown_penalty

        # Data sources
        self.pnl_csv = STATE / "pnl_history.csv"
        self.perf_csv = STATE / "performance_metrics.csv"
        self.strategy_perf = STATE / "strategy_performance.json"
        self.portfolio_json = RUNTIME / "portfolio.json"

        # State history cache
        self.state_history: deque = deque(maxlen=1000)
        self.reward_history: deque = deque(maxlen=1000)

        logger.info(
            f"✅ TradingEnvironment initialized (lookback={lookback_window}, state_size={state_size})"
        )

    def _load_pnl_history(self, days: int = 30) -> pd.DataFrame:
        """Load P&L history from CSV."""
        if not HAS_PANDAS or not self.pnl_csv.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.pnl_csv)
            if "ts" in df.columns:
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
                df = df.dropna(subset=["ts"])
                # Get last N days
                if len(df) > 0:
                    cutoff = df["ts"].max() - timedelta(days=days)
                    df = df[df["ts"] >= cutoff]
            return df
        except Exception as e:
            logger.warning(f"Failed to load P&L history: {e}")
            return pd.DataFrame()

    def _load_performance_metrics(self, days: int = 30) -> pd.DataFrame:
        """Load performance metrics (equity curve)."""
        if not HAS_PANDAS or not self.perf_csv.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.perf_csv)
            if "ts" in df.columns:
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
                df = df.dropna(subset=["ts"])
                if len(df) > 0:
                    cutoff = df["ts"].max() - timedelta(days=days)
                    df = df[df["ts"] >= cutoff]
            return df
        except Exception as e:
            logger.warning(f"Failed to load performance metrics: {e}")
            return pd.DataFrame()

    def _load_strategy_performance(self) -> dict[str, Any]:
        """Load current strategy performance rankings."""
        if not self.strategy_perf.exists():
            return {}

        try:
            return json.loads(self.strategy_perf.read_text())
        except Exception as e:
            logger.warning(f"Failed to load strategy performance: {e}")
            return {}

    def _load_portfolio_state(self) -> dict[str, Any]:
        """Load current portfolio state."""
        if not self.portfolio_json.exists():
            return {}

        try:
            return json.loads(self.portfolio_json.read_text())
        except Exception as e:
            logger.warning(f"Failed to load portfolio state: {e}")
            return {}

    def _compute_market_features(self, pnl_df: pd.DataFrame, perf_df: pd.DataFrame) -> np.ndarray:
        """
        Compute market features from price/performance data.
        Returns: [volatility, trend, momentum, volume_proxy, ...]
        """
        features = np.zeros(8, dtype=np.float32)

        if not HAS_PANDAS or len(perf_df) == 0:
            return features

        try:
            # Volatility (ATR proxy from equity curve)
            if "equity" in perf_df.columns:
                equity = pd.to_numeric(perf_df["equity"], errors="coerce").dropna()
                if len(equity) > 1:
                    returns = equity.pct_change().dropna()
                    features[0] = float(returns.std() * np.sqrt(252))  # Annualized volatility

            # Trend (slope of equity curve)
            if len(equity) > 5:
                x = np.arange(len(equity))
                slope = np.polyfit(x, equity.values, 1)[0]
                features[1] = float(slope / equity.mean() if equity.mean() > 0 else 0)

            # Momentum (recent returns)
            if len(returns) > 0:
                features[2] = float(returns.tail(5).mean() * 252)  # Annualized

            # Volume proxy (trade frequency)
            if len(pnl_df) > 0:
                features[3] = float(len(pnl_df) / max(self.lookback_window, 1))

            # Drawdown
            if "mdd_pct" in perf_df.columns:
                mdd = pd.to_numeric(perf_df["mdd_pct"], errors="coerce")
                if len(mdd) > 0:
                    features[4] = float(mdd.max())

            # Sharpe ratio
            if "rolling_sharpe" in perf_df.columns:
                sharpe = pd.to_numeric(perf_df["rolling_sharpe"], errors="coerce")
                if len(sharpe) > 0:
                    features[5] = float(sharpe.iloc[-1] if len(sharpe) > 0 else 0)

            # Win rate (from P&L)
            if len(pnl_df) > 0 and "pnl" in pnl_df.columns:
                pnl = pd.to_numeric(pnl_df["pnl"], errors="coerce").dropna()
                if len(pnl) > 0:
                    wins = (pnl > 0).sum()
                    features[6] = float(wins / len(pnl) if len(pnl) > 0 else 0)

            # Average P&L
            if len(pnl) > 0:
                features[7] = float(pnl.mean())

        except Exception as e:
            logger.warning(f"Error computing market features: {e}")

        return features

    def _compute_portfolio_features(
        self, portfolio: dict[str, Any], perf_df: pd.DataFrame
    ) -> np.ndarray:
        """Compute portfolio state features."""
        features = np.zeros(6, dtype=np.float32)

        try:
            # Equity
            equity = portfolio.get("equity", 0.0)
            features[0] = float(equity / 100000.0) if equity > 0 else 0.0  # Normalized

            # Cash ratio
            cash = portfolio.get("cash", 0.0)
            features[1] = float(cash / equity if equity > 0 else 1.0)

            # Position count
            positions = portfolio.get("positions", {})
            features[2] = float(len(positions) / 10.0)  # Normalized

            # Current drawdown
            if len(perf_df) > 0 and "mdd_pct" in perf_df.columns:
                mdd = pd.to_numeric(perf_df["mdd_pct"], errors="coerce")
                if len(mdd) > 0:
                    features[3] = float(mdd.iloc[-1] / 100.0)

            # Total P&L
            if "total_pnl" in portfolio:
                features[4] = float(portfolio["total_pnl"] / 10000.0)  # Normalized

            # Position diversity (number of symbols)
            if isinstance(positions, dict):
                symbols = set(positions.keys())
                features[5] = float(len(symbols) / 5.0)  # Normalized

        except Exception as e:
            logger.warning(f"Error computing portfolio features: {e}")

        return features

    def _compute_strategy_performance_features(self, strategy_perf: dict[str, Any]) -> np.ndarray:
        """Compute strategy performance features (8 strategies)."""
        features = np.zeros(16, dtype=np.float32)  # 2 features per strategy (Sharpe, win_rate)

        try:
            ranked = strategy_perf.get("ranked_strategies", [])
            active = strategy_perf.get("active_strategies", [])

            # Create lookup
            strategy_map = {s["strategy"]: s for s in ranked}

            for i, strategy_name in enumerate(STRATEGIES):
                if strategy_name in strategy_map:
                    strat = strategy_map[strategy_name]
                    # Sharpe ratio
                    features[i * 2] = float(strat.get("sharpe", 0.0) / 3.0)  # Normalized
                    # Drawdown (inverse, as lower is better)
                    drawdown = strat.get("drawdown", 50.0)
                    features[i * 2 + 1] = float(1.0 - (drawdown / 50.0))  # Normalized

        except Exception as e:
            logger.warning(f"Error computing strategy features: {e}")

        return features

    def _compute_market_regime_features(self, perf_df: pd.DataFrame) -> np.ndarray:
        """Compute market regime indicators."""
        features = np.zeros(4, dtype=np.float32)

        try:
            if HAS_PANDAS and len(perf_df) > 0:
                # Bull/Bear indicator (trend direction)
                if "equity" in perf_df.columns:
                    equity = pd.to_numeric(perf_df["equity"], errors="coerce").dropna()
                    if len(equity) > 10:
                        recent = equity.tail(10).mean()
                        older = equity.head(10).mean()
                        features[0] = float(1.0 if recent > older else -1.0)

                # Volatility regime
                if "rolling_sharpe" in perf_df.columns:
                    sharpe = pd.to_numeric(perf_df["rolling_sharpe"], errors="coerce")
                    if len(sharpe) > 0:
                        features[1] = float(sharpe.iloc[-1] / 3.0)  # Normalized

                # Stability (low volatility = stable)
                if "equity" in perf_df.columns:
                    equity = pd.to_numeric(perf_df["equity"], errors="coerce").dropna()
                    if len(equity) > 1:
                        returns = equity.pct_change().dropna()
                        features[2] = float(1.0 - min(returns.std() * 10, 1.0))

                # Trend strength
                if len(equity) > 5:
                    x = np.arange(len(equity))
                    slope = np.polyfit(x, equity.values, 1)[0]
                    features[3] = float(abs(slope) / equity.mean() if equity.mean() > 0 else 0)

        except Exception as e:
            logger.warning(f"Error computing regime features: {e}")

        return features

    def get_state(self) -> State:
        """
        Compute current state from market data and portfolio.
        Returns State tuple with all feature vectors.
        """
        # Load data
        pnl_df = self._load_pnl_history(self.lookback_window)
        perf_df = self._load_performance_metrics(self.lookback_window)
        strategy_perf = self._load_strategy_performance()
        portfolio = self._load_portfolio_state()

        # Compute feature vectors
        market_features = self._compute_market_features(pnl_df, perf_df)
        portfolio_features = self._compute_portfolio_features(portfolio, perf_df)
        strategy_features = self._compute_strategy_performance_features(strategy_perf)
        regime_features = self._compute_market_regime_features(perf_df)

        # Combine into full state vector
        full_state = np.concatenate(
            [market_features, portfolio_features, strategy_features, regime_features]
        )

        # Ensure correct size
        if len(full_state) < self.state_size:
            full_state = np.pad(full_state, (0, self.state_size - len(full_state)))
        elif len(full_state) > self.state_size:
            full_state = full_state[: self.state_size]

        state = State(
            market_features=market_features,
            portfolio_features=portfolio_features,
            strategy_performance=strategy_features,
            market_regime=regime_features,
            timestamp=datetime.now(UTC).isoformat(),
        )

        self.state_history.append(state)
        return state

    def compute_reward(
        self,
        previous_state: State | None,
        current_state: State,
        action_taken: np.ndarray | None = None,
    ) -> float:
        """
        Compute reward based on state transition and trade outcomes.

        Args:
            previous_state: Previous state (for computing change)
            current_state: Current state
            action_taken: Strategy weights that were used (optional)

        Returns:
            Reward value (higher is better)
        """
        try:
            # Load recent performance
            perf_df = self._load_performance_metrics(days=30)
            pnl_df = self._load_pnl_history(days=7)  # Recent trades

            reward = 0.0

            # 1. Sharpe ratio component (60% weight)
            if HAS_PANDAS and len(perf_df) > 0 and "rolling_sharpe" in perf_df.columns:
                sharpe = pd.to_numeric(perf_df["rolling_sharpe"], errors="coerce").dropna()
                if len(sharpe) > 0:
                    sharpe_val = sharpe.iloc[-1]
                    # Normalize to [-1, 1] range (assuming Sharpe typically -2 to 3)
                    sharpe_normalized = np.clip(sharpe_val / 3.0, -1.0, 1.0)
                    reward += self.reward_sharpe_weight * sharpe_normalized

            # 2. P&L component (30% weight)
            if HAS_PANDAS and len(pnl_df) > 0:
                if "pnl" in pnl_df.columns:
                    pnl = pd.to_numeric(pnl_df["pnl"], errors="coerce").dropna()
                    if len(pnl) > 0:
                        # Normalize P&L (assuming typical range -1000 to 1000)
                        avg_pnl = pnl.mean()
                        pnl_normalized = np.clip(avg_pnl / 1000.0, -1.0, 1.0)
                        reward += self.reward_pnl_weight * pnl_normalized
                elif len(perf_df) > 0 and "day_pnl" in perf_df.columns:
                    day_pnl = pd.to_numeric(perf_df["day_pnl"], errors="coerce").dropna()
                    if len(day_pnl) > 0:
                        avg_pnl = day_pnl.tail(7).mean()
                        pnl_normalized = np.clip(avg_pnl / 1000.0, -1.0, 1.0)
                        reward += self.reward_pnl_weight * pnl_normalized

            # 3. Drawdown penalty (10% weight, negative)
            if len(perf_df) > 0 and "mdd_pct" in perf_df.columns:
                mdd = pd.to_numeric(perf_df["mdd_pct"], errors="coerce").dropna()
                if len(mdd) > 0:
                    max_dd = mdd.max()
                    # Penalty increases with drawdown (0 to -1)
                    dd_penalty = -np.clip(max_dd / 50.0, 0.0, 1.0)
                    reward += self.reward_drawdown_penalty * dd_penalty

            # Clip reward to reasonable range
            reward = np.clip(reward, -2.0, 2.0)

            self.reward_history.append(reward)
            return float(reward)

        except Exception as e:
            logger.warning(f"Error computing reward: {e}")
            return 0.0

    def get_state_vector(self, state: State) -> np.ndarray:
        """Convert State tuple to flat numpy array for RL agent."""
        return np.concatenate(
            [
                state.market_features,
                state.portfolio_features,
                state.strategy_performance,
                state.market_regime,
            ]
        ).astype(np.float32)

    def reset(self) -> State:
        """Reset environment (for episode-based training)."""
        return self.get_state()

    def step(
        self, action: np.ndarray, previous_state: State | None = None
    ) -> tuple[State, float, bool, dict]:
        """
        Execute one step in the environment.

        Args:
            action: Strategy weights (8 values, should sum to ~1.0)
            previous_state: Previous state for reward computation

        Returns:
            (new_state, reward, done, info)
        """
        # Get current state
        new_state = self.get_state()

        # Compute reward
        reward = self.compute_reward(previous_state, new_state, action)

        # Episode done if drawdown too high or equity too low
        done = False
        if len(self.reward_history) > 10:
            recent_rewards = list(self.reward_history)[-10:]
            if all(r < -0.5 for r in recent_rewards):  # Consistently bad
                done = True

        info = {
            "timestamp": new_state.timestamp,
            "reward_components": {
                "sharpe": self.reward_sharpe_weight,
                "pnl": self.reward_pnl_weight,
                "drawdown": self.reward_drawdown_penalty,
            },
        }

        return new_state, reward, done, info


def main():
    """Test environment."""
    env = TradingEnvironment()
    state = env.get_state()
    print(f"State vector size: {len(env.get_state_vector(state))}")
    print(f"Market features: {state.market_features}")
    print(f"Portfolio features: {state.portfolio_features}")
    reward = env.compute_reward(None, state)
    print(f"Reward: {reward}")


if __name__ == "__main__":
    main()
