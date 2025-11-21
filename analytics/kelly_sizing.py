#!/usr/bin/env python3
"""
NeoLight Kelly Criterion Position Sizing - Phase 3300–3500
==========================================================
World-class position sizing using Kelly Criterion:
- Full Kelly calculation
- Fractional Kelly for safety
- Win rate and reward-risk ratio based sizing
- Dynamic position sizing integration
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "kelly_sizing.log"
logger = logging.getLogger("kelly_sizing")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)


def calculate_kelly_fraction(win_rate: float, reward_risk_ratio: float) -> float:
    """
    Calculate optimal Kelly fraction.

    Kelly Formula: f = (p * b - q) / b
    where:
        f = fraction of capital to bet
        p = win probability
        q = loss probability (1 - p)
        b = reward-risk ratio (average win / average loss)

    Args:
        win_rate: Win probability (0.0 to 1.0, e.g., 0.6 = 60%)
        reward_risk_ratio: Average win size / Average loss size (e.g., 1.5 = 1.5:1)

    Returns:
        Kelly fraction (0.0 to 1.0, typically 0.0 to 0.25 for trading)
    """
    if win_rate <= 0 or win_rate >= 1:
        logger.warning(f"⚠️  Invalid win rate: {win_rate} (must be between 0 and 1)")
        return 0.0

    if reward_risk_ratio <= 0:
        logger.warning(f"⚠️  Invalid reward-risk ratio: {reward_risk_ratio} (must be > 0)")
        return 0.0

    # Kelly formula
    q = 1.0 - win_rate
    kelly = (win_rate * reward_risk_ratio - q) / reward_risk_ratio

    # Clamp to reasonable range (0 to 1)
    kelly = max(0.0, min(kelly, 1.0))

    logger.info(
        f"⚖️  Kelly fraction calculated: {kelly:.4f} (WinRate: {win_rate:.2%}, RR: {reward_risk_ratio:.2f})"
    )

    return kelly


def apply_fractional_kelly(
    win_rate: float, reward_risk_ratio: float, fraction: float = 0.5
) -> float:
    """
    Apply fractional Kelly for safety (reduces position size).

    Fractional Kelly reduces risk while maintaining Kelly's edge.
    Common fractions: 0.25 (quarter Kelly), 0.5 (half Kelly), 0.75 (three-quarter Kelly)

    Args:
        win_rate: Win probability (0.0 to 1.0)
        reward_risk_ratio: Average win / Average loss
        fraction: Fraction of Kelly to use (default 0.5 = half Kelly)

    Returns:
        Position fraction as percent of capital (0.0 to 1.0)
    """
    base_kelly = calculate_kelly_fraction(win_rate, reward_risk_ratio)
    position_fraction = base_kelly * fraction

    logger.info(
        f"✅ Fractional Kelly ({fraction:.0%}): {position_fraction:.4f} "
        f"(Base Kelly: {base_kelly:.4f})"
    )

    return position_fraction


def calculate_adaptive_kelly_fraction(
    base_kelly: float, recent_sharpe: float, recent_win_rate: float, alpha: float = 0.1
) -> float:
    """
    Calculate adaptive Kelly fraction based on recent performance.
    Reduces position size when losing, increases when winning.

    Formula: kelly_t = kelly_base * (1 + α * recent_sharpe)

    Args:
        base_kelly: Base Kelly fraction
        recent_sharpe: Recent Sharpe ratio (30-day rolling)
        recent_win_rate: Recent win rate (30-day rolling)
        alpha: Adaptation rate (default 0.1)

    Returns:
        Adaptive Kelly fraction
    """
    # Adjust based on recent Sharpe
    sharpe_adjustment = 1.0 + (alpha * recent_sharpe)

    # Adjust based on recent win rate (if below 50%, reduce)
    win_rate_adjustment = 1.0 + (alpha * (recent_win_rate - 0.5))

    # Combine adjustments
    adaptive_fraction = base_kelly * sharpe_adjustment * win_rate_adjustment

    # Clamp to reasonable range (0.1 to 1.0 of base Kelly)
    adaptive_fraction = max(0.1 * base_kelly, min(1.0 * base_kelly, adaptive_fraction))

    logger.info(
        f"🔄 Adaptive Kelly: {adaptive_fraction:.4f} "
        f"(Base: {base_kelly:.4f}, Sharpe adj: {sharpe_adjustment:.2f}, Win rate adj: {win_rate_adjustment:.2f})"
    )

    return adaptive_fraction


def calculate_position_size(
    equity: float,
    win_rate: float,
    reward_risk_ratio: float,
    stop_loss_distance: float,
    kelly_fraction: float = 0.5,
    max_risk_per_trade: float = 0.01,
    use_adaptive: bool = False,
    recent_sharpe: float | None = None,
    recent_win_rate: float | None = None,
) -> dict[str, float]:
    """
    Calculate optimal position size using Kelly Criterion and risk management.

    Combines:
    1. Kelly fraction for optimal growth
    2. Stop loss distance for risk control
    3. Max risk per trade limit (e.g., 1% of equity)

    Args:
        equity: Total account equity
        win_rate: Historical win rate (0.0 to 1.0)
        reward_risk_ratio: Average win / Average loss
        stop_loss_distance: Stop loss distance as fraction of entry price (e.g., 0.02 = 2%)
        kelly_fraction: Fraction of Kelly to use (0.5 = half Kelly, default)
        max_risk_per_trade: Maximum risk per trade as fraction of equity (default 0.01 = 1%)

    Returns:
        Dictionary with position sizing details
    """
    # Calculate Kelly-based position fraction
    if use_adaptive and recent_sharpe is not None and recent_win_rate is not None:
        # Use adaptive Kelly
        base_kelly = calculate_kelly_fraction(win_rate, reward_risk_ratio)
        adaptive_kelly = calculate_adaptive_kelly_fraction(
            base_kelly, recent_sharpe, recent_win_rate
        )
        kelly_position_fraction = (
            adaptive_kelly * kelly_fraction
        )  # Apply user-specified fraction on top
    else:
        # Use standard fractional Kelly
        kelly_position_fraction = apply_fractional_kelly(
            win_rate, reward_risk_ratio, kelly_fraction
        )

    # Calculate risk-based position size
    risk_budget = equity * max_risk_per_trade

    # Position size based on stop loss: risk_budget / stop_loss_distance
    if stop_loss_distance <= 0:
        logger.warning("⚠️  Invalid stop loss distance, using default 0.02")
        stop_loss_distance = 0.02

    risk_based_size = risk_budget / stop_loss_distance

    # Kelly-based size: fraction of equity
    kelly_based_size = equity * kelly_position_fraction

    # Use the smaller of the two for safety
    position_size = min(risk_based_size, kelly_based_size)

    # Calculate actual risk
    actual_risk = (position_size * stop_loss_distance) / equity

    result = {
        "position_size": position_size,
        "position_value": position_size,  # For single asset
        "position_fraction": position_size / equity,
        "kelly_fraction": kelly_position_fraction,
        "risk_budget": risk_budget,
        "actual_risk_pct": actual_risk,
        "stop_loss_distance": stop_loss_distance,
        "win_rate": win_rate,
        "reward_risk_ratio": reward_risk_ratio,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    logger.info(
        f"💼 Position size: ${position_size:,.2f} ({position_size / equity:.2%} of equity) | "
        f"Risk: {actual_risk:.2%} | Kelly: {kelly_position_fraction:.2%}"
    )

    return result


def calculate_win_rate_and_rr_from_trades(trades: list) -> tuple[float, float]:
    """
    Calculate win rate and reward-risk ratio from historical trades.

    Args:
        trades: List of trade dictionaries with 'pnl' or ('entry', 'exit', 'side') fields

    Returns:
        (win_rate, reward_risk_ratio)
    """
    if not trades or len(trades) == 0:
        logger.warning("⚠️  No trades provided, using defaults")
        return 0.5, 1.0

    wins = []
    losses = []

    for trade in trades:
        # Try to extract PnL
        pnl = trade.get("pnl") or trade.get("profit") or trade.get("profit_loss")

        if pnl is None:
            # Try to calculate from entry/exit
            entry = trade.get("entry_price")
            exit_price = trade.get("exit_price")
            side = trade.get("side", "buy").lower()

            if entry and exit_price:
                if side == "buy":
                    pnl = (exit_price - entry) / entry
                else:
                    pnl = (entry - exit_price) / entry
            else:
                continue

        if pnl > 0:
            wins.append(pnl)
        elif pnl < 0:
            losses.append(abs(pnl))

    if len(wins) == 0 and len(losses) == 0:
        return 0.5, 1.0

    win_rate = len(wins) / (len(wins) + len(losses))

    if len(wins) == 0:
        reward_risk_ratio = 0.5  # Conservative default
    elif len(losses) == 0:
        reward_risk_ratio = 2.0  # Optimistic default
    else:
        avg_win = sum(wins) / len(wins)
        avg_loss = sum(losses) / len(losses)
        reward_risk_ratio = avg_win / avg_loss if avg_loss > 0 else 2.0

    logger.info(
        f"📊 Win rate: {win_rate:.2%} | "
        f"Reward-Risk: {reward_risk_ratio:.2f} | "
        f"Wins: {len(wins)}, Losses: {len(losses)}"
    )

    return win_rate, reward_risk_ratio


# Example usage
if __name__ == "__main__":
    logger.info("🧪 Testing Kelly Sizing...")

    # Test Kelly calculation
    win_rate = 0.62  # 62% win rate
    rr_ratio = 1.4  # 1.4:1 reward-risk

    kelly = calculate_kelly_fraction(win_rate, rr_ratio)
    print(f"\n✅ Full Kelly: {kelly:.4f}")

    fractional_kelly = apply_fractional_kelly(win_rate, rr_ratio, fraction=0.5)
    print(f"✅ Half Kelly: {fractional_kelly:.4f}")

    # Test position sizing
    equity = 100000.0
    stop_loss = 0.02  # 2% stop loss

    position_info = calculate_position_size(
        equity=equity,
        win_rate=win_rate,
        reward_risk_ratio=rr_ratio,
        stop_loss_distance=stop_loss,
        kelly_fraction=0.5,
        max_risk_per_trade=0.01,
    )

    print(f"\n✅ Position Size: ${position_info['position_size']:,.2f}")
    print(f"✅ Position Fraction: {position_info['position_fraction']:.2%}")
    print(f"✅ Actual Risk: {position_info['actual_risk_pct']:.2%}")
