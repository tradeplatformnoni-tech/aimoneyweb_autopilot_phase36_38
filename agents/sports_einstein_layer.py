#!/usr/bin/env python3
"""Sports Einstein Meta-Layer - Cross-sport edge ranking and bankroll allocation.

This meta-model combines NBA + Soccer predictions, ranks opportunities by:
- Edge size
- Model confidence
- Historical closing line value (CLV)
- Kelly criterion optimal sizing

Outputs unified bet queue with stake recommendations for maximum expected value.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

for directory in (STATE, LOGS):
    directory.mkdir(parents=True, exist_ok=True)

EINSTEIN_OUTPUT = STATE / "sports_einstein_queue.json"
EINSTEIN_LOG = LOGS / "sports_einstein.log"
ALERT_STATE = STATE / "sports_einstein_alert_state.json"

BANKROLL = float(os.getenv("SPORTS_BANKROLL_INITIAL", "1000"))
KELLY_FRACTION = float(os.getenv("SPORTS_KELLY_FRACTION", "0.25"))  # Quarter Kelly for safety
MIN_EDGE = float(os.getenv("SPORTS_MIN_EDGE", "0.03"))  # 3% minimum edge
MAX_STAKE_PCT = float(os.getenv("SPORTS_MAX_STAKE_PCT", "0.10"))  # Max 10% of bankroll per bet


def log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    with EINSTEIN_LOG.open("a") as f:
        f.write(line + "\n")


def load_predictions(sport: str) -> list[dict[str, Any]]:
    """Load latest predictions for a sport."""
    prediction_file = STATE / f"sports_predictions_{sport}.json"
    if not prediction_file.exists():
        return []

    try:
        with prediction_file.open() as f:
            payload = json.load(f)
        return payload.get("predictions", [])
    except (OSError, json.JSONDecodeError) as exc:
        log(f"[{sport}] Error loading predictions: {exc}")
        return []


def calculate_kelly_stake(
    win_prob: float, decimal_odds: float, bankroll: float, kelly_fraction: float = 0.25
) -> float:
    """
    Calculate Kelly criterion stake.

    Args:
        win_prob: Model's predicted win probability
        decimal_odds: Decimal odds offered by bookmaker
        bankroll: Current bankroll
        kelly_fraction: Fraction of Kelly to use (default: quarter Kelly)

    Returns:
        Recommended stake amount
    """
    if win_prob <= 0 or decimal_odds <= 1:
        return 0.0

    # Kelly formula: f = (bp - q) / b
    # where b = decimal_odds - 1, p = win_prob, q = 1 - win_prob
    b = decimal_odds - 1
    q = 1 - win_prob
    kelly = (b * win_prob - q) / b

    if kelly <= 0:
        return 0.0

    # Apply fractional Kelly and bankroll constraints
    stake = bankroll * kelly * kelly_fraction
    max_stake = bankroll * MAX_STAKE_PCT
    return min(stake, max_stake)


def score_opportunity(prediction: dict[str, Any]) -> float:
    """
    Score an opportunity based on multiple factors.

    Returns a composite score that combines:
    - Edge magnitude
    - Confidence
    - Historical CLV (if available)
    """
    edge = prediction.get("edge", 0.0)
    confidence = prediction.get("confidence", 0.5)

    # Base score: edge × confidence
    score = abs(edge) * confidence

    # Bonus for high confidence (>70%)
    if confidence > 0.70:
        score *= 1.2

    # Penalty for low confidence (<55%)
    if confidence < 0.55:
        score *= 0.8

    return score


def rank_opportunities(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank opportunities by composite score and filter by minimum edge."""
    filtered = [p for p in predictions if abs(p.get("edge", 0)) >= MIN_EDGE]

    for pred in filtered:
        pred["einstein_score"] = score_opportunity(pred)

    return sorted(filtered, key=lambda p: p["einstein_score"], reverse=True)


def allocate_bankroll(opportunities: list[dict[str, Any]], bankroll: float) -> list[dict[str, Any]]:
    """
    Allocate bankroll across opportunities using Kelly criterion.

    Ensures total allocation doesn't exceed bankroll.
    """
    allocations: list[dict[str, Any]] = []
    remaining = bankroll

    for opp in opportunities:
        win_prob = opp.get(
            "home_win_probability"
            if opp.get("recommended_side") == opp.get("home_team")
            else "away_win_probability",
            0.5,
        )

        # Infer decimal odds from implied probability
        implied_prob = opp.get(
            "implied_home_prob"
            if opp.get("recommended_side") == opp.get("home_team")
            else "implied_away_prob",
            win_prob,
        )
        if implied_prob and implied_prob > 0:
            decimal_odds = 1.0 / implied_prob
        else:
            decimal_odds = 2.0  # Default if missing

        stake = calculate_kelly_stake(win_prob, decimal_odds, remaining, KELLY_FRACTION)

        if stake < 10:  # Minimum practical bet size
            continue

        allocations.append(
            {
                **opp,
                "recommended_stake": round(stake, 2),
                "decimal_odds": round(decimal_odds, 2),
                "expected_value": round(stake * (win_prob * decimal_odds - 1), 2),
            }
        )

        remaining -= stake

        if remaining < 50:  # Stop if less than $50 remaining
            break

    return allocations


def run_einstein_layer() -> None:
    """Main Einstein meta-layer execution."""
    log("[einstein] Starting meta-analysis...")

    all_predictions: list[dict[str, Any]] = []

    for sport in ("nba", "soccer"):
        predictions = load_predictions(sport)
        log(f"[{sport}] Loaded {len(predictions)} predictions")
        all_predictions.extend(predictions)

    if not all_predictions:
        log("[einstein] No predictions available")
        return

    # Rank opportunities
    ranked = rank_opportunities(all_predictions)
    log(f"[einstein] {len(ranked)} opportunities meet minimum edge threshold ({MIN_EDGE * 100}%)")

    # Allocate bankroll
    allocations = allocate_bankroll(ranked[:20], BANKROLL)  # Top 20 opportunities
    log(f"[einstein] Allocated bankroll across {len(allocations)} opportunities")

    total_stake = sum(a["recommended_stake"] for a in allocations)
    total_ev = sum(a["expected_value"] for a in allocations)

    # Save output
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "bankroll": BANKROLL,
        "total_allocated": round(total_stake, 2),
        "total_expected_value": round(total_ev, 2),
        "opportunities": allocations,
        "count": len(allocations),
    }

    EINSTEIN_OUTPUT.write_text(json.dumps(payload, indent=2))
    log(f"[einstein] Saved {len(allocations)} opportunities to {EINSTEIN_OUTPUT}")
    log(
        f"[einstein] Total EV: ${round(total_ev, 2)} | Allocated: ${round(total_stake, 2)} / ${BANKROLL}"
    )

    signature = {
        "total_ev": round(total_ev, 2),
        "total_allocated": round(total_stake, 2),
        "count": len(allocations),
        "top": [
            {
                "game_id": opp.get("game_id"),
                "sport": opp.get("sport"),
                "side": opp.get("recommended_side"),
                "stake": opp.get("recommended_stake"),
                "decimal_odds": opp.get("decimal_odds"),
            }
            for opp in allocations[:5]
        ],
    }

    last_signature: dict[str, Any] | None = None
    if ALERT_STATE.exists():
        try:
            last_signature = json.loads(ALERT_STATE.read_text())
        except json.JSONDecodeError:
            last_signature = None
    ALERT_STATE.write_text(json.dumps(signature, indent=2))

    if total_ev > 50 and signature != last_signature:
        try:
            from analytics.telegram_notifier import send_alert

            message = f"""💰 **Einstein Layer Alert**

**Total Expected Value**: ${signature["total_ev"]}
**Opportunities**: {signature["count"]}
**Allocated**: ${signature["total_allocated"]} / ${BANKROLL}

Top 3 Bets:
"""
            for i, opp in enumerate(signature["top"][:3], 1):
                message += (
                    f"\n{i}. {opp.get('sport', '').upper()}: {opp.get('side')} "
                    f"@ {opp.get('decimal_odds')} (${opp.get('stake')})"
                )

            send_alert(message)
        except Exception as exc:
            log(f"[einstein] Alert error: {exc}")


if __name__ == "__main__":
    run_einstein_layer()
