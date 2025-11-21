#!/usr/bin/env python3
"""
CLI entry point for the soccer ingestion pipeline.

Usage:
    python scripts/ingest_soccer_data.py --seasons 2022,2023

The script does not require paid APIs; it relies on the ingestion logic
inside `analytics.soccer_ingest` to download historical datasets from FBref and
capture daily odds snapshots via the SofaScore scraper.
"""

from __future__ import annotations

import argparse
import sys

from analytics.soccer_ingest import ingest_daily_odds, run_full_ingestion


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest soccer data without managed APIs")
    parser.add_argument(
        "--seasons",
        type=str,
        default="2024",
        help="Comma-separated list of seasons (e.g., 2024,2023)",
    )
    parser.add_argument(
        "--leagues",
        type=str,
        default="EPL,LaLiga,SerieA",
        help="Comma-separated list of leagues mapped in analytics.soccer_ingest.FBREF_DATASETS",
    )
    parser.add_argument(
        "--odds",
        action="store_true",
        help="Also capture daily odds snapshot during run_full_ingestion (default scraper runs afterwards)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> None:
    args = parse_args(argv)
    seasons = [season.strip() for season in args.seasons.split(",") if season.strip()]
    leagues = [league.strip() for league in args.leagues.split(",") if league.strip()]
    run_full_ingestion(seasons, leagues, ingest_odds=args.odds)
    if not args.odds:
        ingest_daily_odds()


if __name__ == "__main__":
    main(sys.argv[1:])
