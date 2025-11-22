#!/usr/bin/env python3
"""
Strategy Research Agent - Enhanced with Parameter Optimization, Multi-Factor Scoring, and Retirement Logic
Learns from Millionaire Trading Strategies with continuous optimization and performance tracking
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ImportError:
    pd = None
    np = None

# Detect Render environment - use Render paths if in cloud
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"

if RENDER_MODE:
    ROOT = Path("/opt/render/project/src")
else:
    ROOT = Path(os.path.expanduser("~/neolight"))

STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
STRATEGIES_DIR = DATA / "strategies"

STRATEGIES_FILE = STATE / "strategy_performance.json"
PERFORMANCE_CSV = STATE / "performance_metrics.csv"
STRATEGY_SCORES_FILE = STATE / "strategy_scores.json"
OPTIMIZED_PARAMS_FILE = STATE / "strategy_optimized_params.json"
RETIRED_STRATEGIES_FILE = STATE / "retired_strategies.json"

# Retirement thresholds
RETIREMENT_SHARPE_THRESHOLD = 0.3  # Retire if Sharpe < 0.3
RETIREMENT_WIN_RATE_THRESHOLD = 0.40  # Retire if win rate < 40%
RETIREMENT_DRAWDOWN_THRESHOLD = 30.0  # Retire if drawdown > 30%
MIN_TRADES_FOR_RETIREMENT = 20  # Need at least 20 trades before retirement evaluation

# World-Class Strategies Database
MILLIONAIRE_STRATEGIES = {
    "turtle_trading": {
        "name": "Turtle Trading System",
        "description": "Trend following with channel breakout",
        "rules": {
            "entry": "Price breaks 20-day high",
            "exit": "Price breaks 10-day low",
            "stop_loss": "2 ATR below entry",
            "position_sizing": "1% risk per trade",
        },
        "expected_sharpe": 1.5,
        "drawdown": 15,
    },
    "mean_reversion_rsi": {
        "name": "RSI Mean Reversion",
        "description": "Buy oversold, sell overbought",
        "rules": {
            "entry": "RSI < 30",
            "exit": "RSI > 70",
            "stop_loss": "3% below entry",
            "position_sizing": "Kelly Criterion",
        },
        "expected_sharpe": 1.2,
        "drawdown": 10,
    },
    "momentum_sma_crossover": {
        "name": "Moving Average Crossover",
        "description": "Golden Cross / Death Cross",
        "rules": {
            "entry": "SMA 50 crosses above SMA 200",
            "exit": "SMA 50 crosses below SMA 200",
            "stop_loss": "5% trailing stop",
            "position_sizing": "Risk parity",
        },
        "expected_sharpe": 1.0,
        "drawdown": 20,
    },
    "breakout_trading": {
        "name": "Breakout Trading",
        "description": "Trade breakouts from consolidation",
        "rules": {
            "entry": "Price breaks resistance (Bollinger Band upper)",
            "exit": "Price breaks support (Bollinger Band lower)",
            "stop_loss": "Below breakout level",
            "position_sizing": "ATR-based",
        },
        "expected_sharpe": 1.3,
        "drawdown": 12,
    },
    "pairs_trading": {
        "name": "Pairs Trading / Statistical Arbitrage",
        "description": "Trade correlated pairs when spread diverges",
        "rules": {
            "entry": "Z-score of spread > 2",
            "exit": "Z-score of spread < 0",
            "stop_loss": "Z-score > 3",
            "position_sizing": "Equal dollar",
        },
        "expected_sharpe": 1.8,
        "drawdown": 8,
    },
    "macd_momentum": {
        "name": "MACD Momentum",
        "description": "Trade MACD crossovers",
        "rules": {
            "entry": "MACD crosses above signal line",
            "exit": "MACD crosses below signal line",
            "stop_loss": "Below recent low",
            "position_sizing": "Volatility-based",
        },
        "expected_sharpe": 1.1,
        "drawdown": 15,
    },
    "bollinger_bands": {
        "name": "Bollinger Bands Mean Reversion",
        "description": "Buy at lower band, sell at upper band",
        "rules": {
            "entry": "Price touches lower Bollinger Band",
            "exit": "Price touches upper Bollinger Band",
            "stop_loss": "2% below lower band",
            "position_sizing": "Fixed percentage",
        },
        "expected_sharpe": 1.4,
        "drawdown": 10,
    },
    "vix_strategy": {
        "name": "VIX Fear Greed",
        "description": "Buy when VIX spikes (fear), sell when VIX drops",
        "rules": {
            "entry": "VIX > 30 (extreme fear)",
            "exit": "VIX < 20 (greed)",
            "stop_loss": "20% trailing stop",
            "position_sizing": "Inverse volatility",
        },
        "expected_sharpe": 1.6,
        "drawdown": 25,
    },
}


def load_actual_performance() -> dict[str, dict[str, Any]]:
    """Load actual performance data from CSV and JSON files."""
    performance = {}

    # Load from performance_metrics.csv
    if PERFORMANCE_CSV.exists() and pd:
        try:
            df = pd.read_csv(PERFORMANCE_CSV)
            if len(df) > 0:
                latest = df.iloc[-1]
                performance["overall"] = {
                    "sharpe_30d": float(latest.get("sharpe_30d", 0.0))
                    if pd.notna(latest.get("sharpe_30d"))
                    else 0.0,
                    "drawdown": float(latest.get("drawdown", 0.0))
                    if pd.notna(latest.get("drawdown"))
                    else 0.0,
                    "win_rate_7d": float(latest.get("win_rate_7d", 0.0))
                    if pd.notna(latest.get("win_rate_7d"))
                    else 0.0,
                    "trades_7d": float(latest.get("trades_7d", 0.0))
                    if pd.notna(latest.get("trades_7d"))
                    else 0.0,
                    "equity": float(latest.get("equity", 100000.0))
                    if pd.notna(latest.get("equity"))
                    else 100000.0,
                }
        except Exception as e:
            print(f"[strategy_research] Error loading performance CSV: {e}", flush=True)

    # Load from strategy_scores.json
    if STRATEGY_SCORES_FILE.exists():
        try:
            scores_data = json.loads(STRATEGY_SCORES_FILE.read_text())
            performance["strategy_scores"] = scores_data.get("scores", {})
        except Exception as e:
            print(f"[strategy_research] Error loading strategy scores: {e}", flush=True)

    return performance


def optimize_strategy_parameters(
    strategy_name: str, param_space: dict[str, list[Any]]
) -> dict[str, Any]:
    """
    Optimize strategy parameters using grid search.

    Args:
        strategy_name: Name of the strategy
        param_space: Dictionary of parameter names to lists of possible values
        Example: {"rsi_period": [14, 21, 28], "rsi_oversold": [25, 30, 35]}

    Returns:
        Dictionary with optimized parameters and performance metrics
    """
    if not np or not param_space:
        return {"error": "Parameter optimization requires numpy and parameter space"}

    best_params = None
    best_score = float("-inf")
    best_metrics = {}

    # Generate all parameter combinations
    param_names = list(param_space.keys())
    param_values = list(param_space.values())
    combinations = list(product(*param_values))

    print(
        f"[strategy_research] Optimizing {strategy_name}: {len(combinations)} parameter combinations",
        flush=True,
    )

    # Simplified optimization: score based on expected performance
    # In production, would backtest each combination
    for combo in combinations[:50]:  # Limit to 50 combinations for performance
        params = dict(zip(param_names, combo))

        # Calculate score based on parameter values
        # Higher RSI periods = more stable but slower signals
        # Lower oversold thresholds = more frequent but riskier entries
        score = 0.0

        if "rsi_period" in params:
            # Prefer moderate RSI periods (14-21)
            rsi_period = params["rsi_period"]
            if 14 <= rsi_period <= 21:
                score += 0.3
            elif 21 < rsi_period <= 28:
                score += 0.2

        if "rsi_oversold" in params:
            # Prefer RSI oversold around 30 (balanced)
            rsi_oversold = params["rsi_oversold"]
            if 28 <= rsi_oversold <= 32:
                score += 0.3
            elif 25 <= rsi_oversold < 28:
                score += 0.2

        if "sma_fast" in params and "sma_slow" in params:
            # Prefer reasonable SMA ratios (e.g., 50/200)
            sma_fast = params["sma_fast"]
            sma_slow = params["sma_slow"]
            ratio = sma_slow / sma_fast if sma_fast > 0 else 0
            if 3 <= ratio <= 5:  # Good ratio (e.g., 50/200 = 4)
                score += 0.4

        if score > best_score:
            best_score = score
            best_params = params
            best_metrics = {"optimization_score": score, "method": "grid_search"}

    if best_params:
        result = {
            "strategy": strategy_name,
            "optimized_parameters": best_params,
            "metrics": best_metrics,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    return {"error": "Optimization failed"}


def backtest_strategy(
    strategy_name: str, strategy_rules: dict, price_data: Any | None = None
) -> dict[str, Any]:
    """Backtest a strategy on historical data."""
    if price_data is None or pd is None:
        return {"error": "No price data available"}

    # Simplified backtest logic
    # In production, would implement full strategy rules

    result = {
        "strategy": strategy_name,
        "sharpe_ratio": strategy_rules.get("expected_sharpe", 1.0),
        "max_drawdown": strategy_rules.get("drawdown", 15),
        "win_rate": 0.55,  # Placeholder
        "total_return": 0.0,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    return result


def calculate_enhanced_score(
    strategy_name: str, strategy: dict[str, Any], actual_performance: dict[str, Any]
) -> float:
    """
    Calculate enhanced multi-factor score for a strategy.
    Combines expected performance with actual performance data.
    """
    # Base score from expected metrics (40% weight)
    expected_sharpe = strategy.get("expected_sharpe", 1.0)
    expected_drawdown = strategy.get("drawdown", 15)
    base_score = expected_sharpe * 0.6 - (expected_drawdown / 100) * 0.4

    # Actual performance adjustment (60% weight if available)
    actual_score = 0.0
    weight_actual = 0.0

    # Check for strategy-specific performance
    strategy_scores = actual_performance.get("strategy_scores", {})
    if strategy_name in strategy_scores:
        strat_data = strategy_scores[strategy_name]
        stats = strat_data.get("stats", {})
        win_rate = stats.get("win_rate", 0.5)
        avg_pnl = stats.get("avg_pnl", 0.0)
        total_trades = stats.get("total_decisions", 0)

        if total_trades >= MIN_TRADES_FOR_RETIREMENT:
            # Actual performance score
            actual_score = (
                (win_rate * 0.5)
                + (min(avg_pnl / 100, 1.0) * 0.3)
                + (min(total_trades / 100, 1.0) * 0.2)
            )
            weight_actual = 0.6
    else:
        # Use overall performance if strategy-specific data not available
        overall = actual_performance.get("overall", {})
        if overall:
            sharpe = overall.get("sharpe_30d", 0.0)
            win_rate = overall.get("win_rate_7d", 0.5)
            drawdown = overall.get("drawdown", 0.0)

            if sharpe > 0 or win_rate > 0:
                actual_score = (sharpe / 2.0 * 0.4) + (win_rate * 0.4) - (drawdown / 100 * 0.2)
                actual_score = max(0.0, min(1.0, actual_score))  # Clamp to [0, 1]
                weight_actual = 0.3  # Lower weight for overall data

    # Combined score
    if weight_actual > 0:
        final_score = base_score * (1 - weight_actual) + actual_score * weight_actual
    else:
        final_score = base_score

    return float(final_score)


def rank_strategies() -> list[dict[str, Any]]:
    """Rank strategies by enhanced multi-factor scoring."""
    # Load actual performance data
    actual_performance = load_actual_performance()

    # Load retired strategies
    retired_strategies = set()
    if RETIRED_STRATEGIES_FILE.exists():
        try:
            retired_data = json.loads(RETIRED_STRATEGIES_FILE.read_text())
            retired_strategies = set(retired_data.get("retired", []))
        except:
            pass

    ranked = []
    for name, strategy in MILLIONAIRE_STRATEGIES.items():
        # Skip retired strategies
        if name in retired_strategies:
            continue

        # Calculate enhanced score
        score = calculate_enhanced_score(name, strategy, actual_performance)

        # Get actual performance metrics if available
        actual_sharpe = None
        actual_win_rate = None
        actual_drawdown = None

        strategy_scores = actual_performance.get("strategy_scores", {})
        if name in strategy_scores:
            stats = strategy_scores[name].get("stats", {})
            actual_win_rate = stats.get("win_rate")

        overall = actual_performance.get("overall", {})
        if overall:
            actual_sharpe = overall.get("sharpe_30d")
            actual_drawdown = overall.get("drawdown")

        ranked.append(
            {
                "strategy": name,
                "name": strategy["name"],
                "score": score,
                "sharpe": strategy["expected_sharpe"],
                "drawdown": strategy["drawdown"],
                "actual_sharpe": actual_sharpe,
                "actual_win_rate": actual_win_rate,
                "actual_drawdown": actual_drawdown,
                "retired": False,
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def evaluate_strategy_retirement(strategy_name: str, strategy_performance: dict[str, Any]) -> bool:
    """
    Evaluate if a strategy should be retired based on performance thresholds.

    Args:
        strategy_name: Name of the strategy
        strategy_performance: Performance metrics for the strategy

    Returns:
        True if strategy should be retired, False otherwise
    """
    sharpe = strategy_performance.get("sharpe", 0.0)
    win_rate = strategy_performance.get("win_rate", 0.5)
    drawdown = strategy_performance.get("drawdown", 0.0)
    trades = strategy_performance.get("trades", 0)

    # Need minimum trades before retirement evaluation
    if trades < MIN_TRADES_FOR_RETIREMENT:
        return False

    # Retirement conditions
    if sharpe < RETIREMENT_SHARPE_THRESHOLD:
        return True

    if win_rate < RETIREMENT_WIN_RATE_THRESHOLD:
        return True

    if drawdown > RETIREMENT_DRAWDOWN_THRESHOLD:
        return True

    return False


def retire_strategy(strategy_name: str, reason: str) -> None:
    """Retire a strategy (disable it from active use)."""
    if RETIRED_STRATEGIES_FILE.exists():
        try:
            retired_data = json.loads(RETIRED_STRATEGIES_FILE.read_text())
            retired = set(retired_data.get("retired", []))
        except:
            retired = set()
    else:
        retired = set()

    retired.add(strategy_name)

    # Get existing retirement history
    existing_history = []
    if RETIRED_STRATEGIES_FILE.exists():
        try:
            existing_data = json.loads(RETIRED_STRATEGIES_FILE.read_text())
            existing_history = existing_data.get("retirement_history", [])
        except:
            existing_history = []

    retired_data = {
        "retired": list(retired),
        "retirement_history": existing_history
        + [
            {
                "strategy": strategy_name,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ],
    }

    RETIRED_STRATEGIES_FILE.write_text(json.dumps(retired_data, indent=2))
    print(f"[strategy_research] ⚠️ Retired strategy: {strategy_name} - {reason}", flush=True)


def generate_signal(
    strategy_name: str, current_price: float, price_history: list[float]
) -> str | None:
    """Generate signal based on strategy rules."""
    strategy = MILLIONAIRE_STRATEGIES.get(strategy_name)
    if not strategy:
        return None

    if len(price_history) < 50:
        return None

    rules = strategy["rules"]

    # Implement strategy-specific logic
    if strategy_name == "turtle_trading":
        high_20 = max(price_history[-20:])
        if current_price > high_20:
            return "buy"
        low_10 = min(price_history[-10:])
        if current_price < low_10:
            return "sell"

    elif strategy_name == "mean_reversion_rsi":
        if np:
            returns = np.diff(price_history[-30:])
            gains = returns[returns > 0]
            losses = -returns[returns < 0]
            if len(losses) > 0:
                rs = gains.mean() / losses.mean() if losses.mean() > 0 else 100
                rsi = 100 - (100 / (1 + rs))
                if rsi < 30:
                    return "buy"
                elif rsi > 70:
                    return "sell"

    elif strategy_name == "momentum_sma_crossover":
        if len(price_history) >= 200:
            sma_50 = sum(price_history[-50:]) / 50
            sma_200 = sum(price_history[-200:]) / 200
            prev_sma_50 = sum(price_history[-51:-1]) / 50
            prev_sma_200 = sum(price_history[-201:-1]) / 200

            if sma_50 > sma_200 and prev_sma_50 <= prev_sma_200:
                return "buy"
            elif sma_50 < sma_200 and prev_sma_50 >= prev_sma_200:
                return "sell"

    return None


def main():
    """Main strategy research loop with optimization and retirement evaluation."""
    print(
        f"[strategy_research] Starting enhanced strategy research @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    optimization_cycle = 0
    retirement_check_cycle = 0

    while True:
        try:
            # Load actual performance data
            actual_performance = load_actual_performance()

            # === PARAMETER OPTIMIZATION (every 6 hours) ===
            optimization_cycle += 1
            if optimization_cycle >= 6:  # Every 6 hours
                optimization_cycle = 0
                print("[strategy_research] Running parameter optimization...", flush=True)

                # Optimize RSI strategy parameters
                rsi_param_space = {
                    "rsi_period": [14, 21, 28],
                    "rsi_oversold": [25, 30, 35],
                    "rsi_overbought": [65, 70, 75],
                }
                rsi_optimization = optimize_strategy_parameters(
                    "mean_reversion_rsi", rsi_param_space
                )

                # Optimize SMA crossover parameters
                sma_param_space = {"sma_fast": [20, 50, 100], "sma_slow": [50, 100, 200]}
                sma_optimization = optimize_strategy_parameters(
                    "momentum_sma_crossover", sma_param_space
                )

                # Save optimized parameters
                optimized_params = {
                    "mean_reversion_rsi": rsi_optimization.get("optimized_parameters", {}),
                    "momentum_sma_crossover": sma_optimization.get("optimized_parameters", {}),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                OPTIMIZED_PARAMS_FILE.write_text(json.dumps(optimized_params, indent=2))
                print("[strategy_research] ✅ Parameter optimization complete", flush=True)

            # === RETIREMENT EVALUATION (every 12 hours) ===
            retirement_check_cycle += 1
            if retirement_check_cycle >= 12:  # Every 12 hours
                retirement_check_cycle = 0
                print("[strategy_research] Evaluating strategy retirement...", flush=True)

                # Check each strategy for retirement
                strategy_scores = actual_performance.get("strategy_scores", {})
                overall = actual_performance.get("overall", {})

                for strategy_name in MILLIONAIRE_STRATEGIES:
                    # Get strategy performance
                    strategy_perf = {}
                    if strategy_name in strategy_scores:
                        stats = strategy_scores[strategy_name].get("stats", {})
                        strategy_perf = {
                            "sharpe": overall.get("sharpe_30d", 0.0),
                            "win_rate": stats.get("win_rate", 0.5),
                            "drawdown": overall.get("drawdown", 0.0),
                            "trades": stats.get("total_decisions", 0),
                        }
                    elif overall:
                        strategy_perf = {
                            "sharpe": overall.get("sharpe_30d", 0.0),
                            "win_rate": overall.get("win_rate_7d", 0.5),
                            "drawdown": overall.get("drawdown", 0.0),
                            "trades": overall.get("trades_7d", 0),
                        }

                    # Evaluate retirement
                    if strategy_perf and evaluate_strategy_retirement(strategy_name, strategy_perf):
                        reason = f"Sharpe: {strategy_perf.get('sharpe', 0):.2f}, Win Rate: {strategy_perf.get('win_rate', 0):.2%}, Drawdown: {strategy_perf.get('drawdown', 0):.2f}%"
                        retire_strategy(strategy_name, reason)

            # === RANK STRATEGIES (every hour) ===
            ranked = rank_strategies()

            # Save performance data
            performance = {
                "ranked_strategies": ranked,
                "active_strategies": ranked[:3],  # Top 3 strategies
                "optimization_cycle": optimization_cycle,
                "retirement_check_cycle": retirement_check_cycle,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            STRATEGIES_FILE.write_text(json.dumps(performance, indent=2))

            print("[strategy_research] Top strategies:", flush=True)
            for i, strat in enumerate(ranked[:5], 1):
                actual_info = ""
                if strat.get("actual_sharpe") is not None:
                    actual_info = f" (Actual Sharpe: {strat['actual_sharpe']:.2f})"
                if strat.get("actual_win_rate") is not None:
                    actual_info += f" (Win Rate: {strat['actual_win_rate']:.2%})"
                print(
                    f"  {i}. {strat['name']}: Score {strat['score']:.3f}, Expected Sharpe {strat['sharpe']:.2f}{actual_info}",
                    flush=True,
                )

            # Update every hour
            time.sleep(3600)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[strategy_research] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(600)


if __name__ == "__main__":
    main()
