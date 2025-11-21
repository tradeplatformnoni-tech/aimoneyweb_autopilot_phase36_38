#!/usr/bin/env python3
"""Fetch today's live games and generate recommendations."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "f89c81c096msh0e367842c4a9cedp172050jsn8f96a4f06504")
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(UTC).strftime("%Y-%m-%d")


def fetch_nba_games_today():
    """Fetch NBA games for today using RapidAPI."""
    games = []
    try:
        # Try RapidAPI Odds API for NBA fixtures
        url = "https://odds-api1.p.rapidapi.com/fixtures/basketball_nba"
        headers = {
            "x-rapidapi-host": "odds-api1.p.rapidapi.com",
            "x-rapidapi-key": RAPIDAPI_KEY,
        }
        params = {"date": TODAY}

        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("data", [])

            for fix in fixtures:
                commence_time = fix.get("commence_time", "")
                if TODAY in commence_time:
                    games.append(
                        {
                            "sport": "nba",
                            "game_id": fix.get("id", ""),
                            "home_team": fix.get("home_team", ""),
                            "away_team": fix.get("away_team", ""),
                            "scheduled": commence_time,
                            "status": "scheduled",
                        }
                    )

        print(f"✅ Found {len(games)} NBA games for today")
    except Exception as e:
        print(f"⚠️ NBA fetch error: {e}")

    return games


def fetch_soccer_games_today():
    """Fetch soccer games for today using RapidAPI."""
    games = []
    try:
        # Try RapidAPI Odds API for soccer fixtures
        url = "https://odds-api1.p.rapidapi.com/fixtures/soccer_epl"
        headers = {
            "x-rapidapi-host": "odds-api1.p.rapidapi.com",
            "x-rapidapi-key": RAPIDAPI_KEY,
        }
        params = {"date": TODAY}

        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("data", [])

            for fix in fixtures:
                commence_time = fix.get("commence_time", "")
                if TODAY in commence_time:
                    games.append(
                        {
                            "sport": "soccer",
                            "game_id": fix.get("id", ""),
                            "home_team": fix.get("home_team", ""),
                            "away_team": fix.get("away_team", ""),
                            "scheduled": commence_time,
                            "status": "scheduled",
                        }
                    )

        print(f"✅ Found {len(games)} soccer games for today")
    except Exception as e:
        print(f"⚠️ Soccer fetch error: {e}")

    return games


def save_today_games(games):
    """Save today's games to state file."""
    output_file = STATE / "today_games.json"
    payload = {
        "date": TODAY,
        "timestamp": datetime.now(UTC).isoformat(),
        "games": games,
        "count": len(games),
    }
    output_file.write_text(json.dumps(payload, indent=2))
    print(f"✅ Saved {len(games)} games to {output_file}")
    return output_file


def main():
    print(f"🏀 Fetching Live Games for Today ({TODAY})")
    print("=" * 50)
    print("")

    all_games = []

    # Fetch NBA games
    print("1. Fetching NBA games...")
    nba_games = fetch_nba_games_today()
    all_games.extend(nba_games)

    # Fetch soccer games
    print("")
    print("2. Fetching soccer games...")
    soccer_games = fetch_soccer_games_today()
    all_games.extend(soccer_games)

    # Save games
    print("")
    print("3. Saving games...")
    if all_games:
        save_today_games(all_games)
        print("")
        print(f"✅ Total games found: {len(all_games)}")
        print("")
        print("Top games:")
        for i, game in enumerate(all_games[:10], 1):
            scheduled = game.get("scheduled", "TBD")
            time_part = scheduled.split("T")[1][:5] if "T" in scheduled else "TBD"
            print(
                f"   {i}. {game['sport'].upper()}: {game['away_team']} @ {game['home_team']} - {time_part}"
            )
    else:
        print("⚠️ No games found for today")
        print("   The system will use historical predictions")

    return all_games


if __name__ == "__main__":
    main()
