#!/usr/bin/env python3
"""CLI wrapper for NBA ingestion without managed APIs."""

from __future__ import annotations

import argparse
import sys

from analytics.nba_ingest import ingest_injuries, run_full_ingestion


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest NBA datasets into local cache")
    parser.add_argument(
        "--seasons",
        default="2024",
        help="Comma-separated NBA seasons to ingest (e.g. 2024,2023)",
    )
    parser.add_argument(
        "--no-odds",
        action="store_true",
        help="Skip odds ingestion",
    )
    parser.add_argument(
        "--injuries-only",
        action="store_true",
        help="Only refresh the injury snapshot",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> None:
    args = parse_args(argv)
    seasons = [season.strip() for season in args.seasons.split(",") if season.strip()]

    if args.injuries_only:
        ingest_injuries()
        return

    run_full_ingestion(
        seasons,
        ingest_odds_snapshot=not args.no_odds,
        ingest_injury_snapshot=True,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
