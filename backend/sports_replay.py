"""Sports analytics replay and evaluation engine.

Running this script recomputes historical metrics for each configured sport
using the shared feature builder and ensemble training logic. Results are
written to `state/sports_backtest_summary.json` for dashboard consumption.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from agents.sports_analytics_agent import (
    SPORTS,
    YEARS_OF_HISTORY,
    FeatureBuilder,
    generate_season_list,
    load_game_history,
    load_odds_history,
    train_ensemble,
)
from analytics.sports_data_manager import backfill_odds_history, backfill_sportradar_history

ROOT = Path("~/neolight").expanduser()
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)
SUMMARY_FILE = STATE / "sports_backtest_summary.json"


def run_once() -> dict[str, dict]:
    summary: dict[str, dict] = {"generated_at": datetime.now(UTC).isoformat()}

    for sport in SPORTS:
        seasons = generate_season_list(YEARS_OF_HISTORY)
        backfill_sportradar_history(sport, seasons)
        backfill_odds_history(sport, seasons)

        games = load_game_history(sport, seasons)
        odds = load_odds_history(sport, seasons)
        builder = FeatureBuilder(sport, games, odds)
        X, y, metadata, _ = builder.build_datasets()

        if len(X) < 20:
            summary[sport] = {
                "status": "insufficient_data",
                "training_samples": len(X),
            }
            continue

        _, _, metrics = train_ensemble(X, y, metadata)
        summary[sport] = {
            "status": "ok",
            "training_samples": len(X),
            "metrics": metrics,
        }

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    report = run_once()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
