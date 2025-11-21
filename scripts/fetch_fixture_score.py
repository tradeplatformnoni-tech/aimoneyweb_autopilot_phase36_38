#!/usr/bin/env python3
"""Fetch a single fixture score from RapidAPI as a fallback snapshot."""

from __future__ import annotations

import argparse
import sys

from analytics.sports_data_manager import fetch_fixture_score


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch fixture score via RapidAPI fallback.")
    parser.add_argument("fixture_id", help="Fixture identifier used by RapidAPI odds API")
    return parser.parse_args(argv)


def main(argv: list[str]) -> None:
    args = parse_args(argv)
    payload = fetch_fixture_score(args.fixture_id)
    if not payload:
        print(f"⚠️  No score data returned for fixture {args.fixture_id}")
        return
    print(f"✅ Score snapshot stored for fixture {args.fixture_id}")


if __name__ == "__main__":
    main(sys.argv[1:])
