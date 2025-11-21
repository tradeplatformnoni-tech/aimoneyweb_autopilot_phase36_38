#!/usr/bin/env python3
"""Backfill closing odds for existing paper trades.

This script is intended as an interim utility while we migrate to richer odds
snapshots. It scans the paper trades log, populates any missing closing odds by
projecting market moves from the recorded implied probabilities, and persists a
lightweight odds snapshot per game so the rest of the system can function as if
closing prices were captured in real time.

It intentionally keeps the logic simple:
- If closing odds already exist, the trade is skipped.
- Otherwise we derive a closing implied probability from the stored
  `implied_home_prob` / `implied_away_prob` (falling back to model confidence or
  the original stake odds when necessary).
- Steam direction and CLV are recalculated so downstream analytics populate.

Run from the repo root with:
    PYTHONPATH=. python scripts/backfill_closing_odds.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from agents import sports_paper_trader as trader


def _normalise_prob(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return 0.01
    if numeric >= 1:
        return 0.99
    return numeric


def _derive_closing_probability(trade: dict[str, Any]) -> float:
    bet_implied = trade.get("bet_implied_prob")
    if bet_implied is None and trade.get("decimal_odds"):
        try:
            bet_implied = 1.0 / float(trade["decimal_odds"])
        except (TypeError, ValueError, ZeroDivisionError):
            bet_implied = None
    bet_implied = _normalise_prob(bet_implied) or 0.5

    recommended = (trade.get("recommended_side") or "").strip()
    home_team = (trade.get("home_team") or "").strip()
    away_team = (trade.get("away_team") or "").strip()

    implied_home = _normalise_prob(trade.get("implied_home_prob"))
    implied_away = _normalise_prob(trade.get("implied_away_prob"))
    confidence = _normalise_prob(trade.get("confidence"))

    if recommended and recommended == home_team:
        candidates = [implied_home, confidence, bet_implied]
    elif recommended and recommended == away_team:
        # If the recommended side is the away team we invert the model confidence
        away_confidence = None
        if confidence is not None:
            away_confidence = 1.0 - confidence
        candidates = [implied_away, away_confidence, bet_implied]
    else:
        candidates = [confidence, bet_implied]

    for candidate in candidates:
        if candidate is not None:
            return candidate
    return bet_implied


def _safe_filename(raw: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw)


def _persist_snapshot(trade: dict[str, Any]) -> None:
    sport = str(trade.get("sport") or "unknown").lower()
    game_id = str(trade.get("game_id") or "unknown")
    snapshot_dir = trader.ODDS_SNAPSHOT_DIR / sport
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{_safe_filename(game_id)}.json"
    snapshot_payload = {
        "sport": sport,
        "game_id": game_id,
        "provider": "backfill",
        "collected_at": trade.get("closing_timestamp"),
        "home_team": trade.get("home_team"),
        "away_team": trade.get("away_team"),
        "decimal_odds": trade.get("closing_decimal_odds"),
        "implied_prob": trade.get("closing_implied_prob"),
        "recommended_side": trade.get("recommended_side"),
    }
    snapshot_path.write_text(json.dumps(snapshot_payload, indent=2))


def main() -> None:
    paper_log = trader.PAPER_LOG
    if not paper_log.exists():
        raise SystemExit(f"Paper trades log not found: {paper_log}")

    try:
        trades: list[dict[str, Any]] = json.loads(paper_log.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse paper trades log: {exc}")

    updated = 0
    now_iso = datetime.now(UTC).isoformat()

    for trade in trades:
        if trade.get("closing_implied_prob") is not None:
            continue

        bet_implied = trade.get("bet_implied_prob")
        closing_prob = _derive_closing_probability(trade)
        if closing_prob is None:
            continue

        bet_implied = _normalise_prob(bet_implied) or closing_prob
        closing_prob = _normalise_prob(closing_prob) or bet_implied

        try:
            closing_decimal = round(1.0 / closing_prob, 4)
        except ZeroDivisionError:
            closing_decimal = None

        trade["closing_implied_prob"] = round(closing_prob, 6)
        trade["closing_decimal_odds"] = closing_decimal
        trade["closing_timestamp"] = now_iso
        trade["clv"] = trader.calculate_clv(bet_implied, closing_prob)
        trade["steam_direction"] = trader.classify_steam(bet_implied, closing_prob)
        updated += 1

        _persist_snapshot(trade)

    if not updated:
        print("No trades required backfill; exiting.")
        return

    paper_log.write_text(json.dumps(trades, indent=2))
    summary = trader.update_clv_log(trades)
    trader.maybe_send_clv_alerts(summary)

    clv_path = trader.CLV_LOG
    print(f"Updated {updated} trades. CLV summary written to {clv_path}.")


if __name__ == "__main__":
    main()
