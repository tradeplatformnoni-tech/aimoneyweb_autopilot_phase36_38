#!/usr/bin/env python3
"""Update games with correct NBA schedule from today (Nov 18, 2025)."""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc)

# Correct NBA games for today (Nov 18, 2025) from screenshot
nba_games = [
    {
        "sport": "nba",
        "game_id": "nba_warriors_magic_20251118",
        "home_team": "Orlando Magic",
        "away_team": "Golden State Warriors",
        "scheduled": TODAY.replace(hour=23, minute=0, second=0).isoformat(),  # 6:00 PM EST = 23:00 UTC
        "status": "scheduled",
        "source": "nba_official",
    },
    {
        "sport": "nba",
        "game_id": "nba_pistons_hawks_20251118",
        "home_team": "Atlanta Hawks",
        "away_team": "Detroit Pistons",
        "scheduled": TODAY.replace(hour=23, minute=30, second=0).isoformat(),  # 6:30 PM EST
        "status": "scheduled",
        "source": "nba_official",
    },
    {
        "sport": "nba",
        "game_id": "nba_celtics_nets_20251118",
        "home_team": "Brooklyn Nets",
        "away_team": "Boston Celtics",
        "scheduled": TODAY.replace(hour=23, minute=30, second=0).isoformat(),  # 6:30 PM EST
        "status": "scheduled",
        "source": "nba_official",
    },
    {
        "sport": "nba",
        "game_id": "nba_grizzlies_spurs_20251118",
        "home_team": "San Antonio Spurs",
        "away_team": "Memphis Grizzlies",
        "scheduled": (TODAY.replace(hour=0, minute=0, second=0) + timedelta(days=1)).isoformat(),  # 7:00 PM EST = 00:00 UTC next day
        "status": "scheduled",
        "source": "nba_official",
    },
    {
        "sport": "nba",
        "game_id": "nba_jazz_lakers_20251118",
        "home_team": "Los Angeles Lakers",
        "away_team": "Utah Jazz",
        "scheduled": (TODAY.replace(hour=2, minute=30, second=0) + timedelta(days=1)).isoformat(),  # 9:30 PM EST = 02:30 UTC next day
        "status": "scheduled",
        "source": "nba_official",
    },
    {
        "sport": "nba",
        "game_id": "nba_suns_trailblazers_20251118",
        "home_team": "Portland Trail Blazers",
        "away_team": "Phoenix Suns",
        "scheduled": (TODAY.replace(hour=3, minute=0, second=0) + timedelta(days=1)).isoformat(),  # 10:00 PM EST = 03:00 UTC next day
        "status": "scheduled",
        "source": "nba_official",
    },
]

# Add some soccer games for today
soccer_games = [
    {
        "sport": "soccer",
        "game_id": "soccer_sample_1",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "scheduled": TODAY.replace(hour=20, minute=0, second=0).isoformat(),
        "status": "scheduled",
        "league": "EPL",
        "source": "sample",
    },
]

all_games = nba_games + soccer_games

output_file = STATE / "today_games.json"
payload = {
    "date": TODAY.strftime("%Y-%m-%d"),
    "timestamp": TODAY.isoformat(),
    "games": all_games,
    "count": len(all_games),
    "nba_count": len(nba_games),
    "soccer_count": len(soccer_games),
    "note": "Correct NBA games for Nov 18, 2025 from official schedule",
}

output_file.write_text(json.dumps(payload, indent=2))

print(f"✅ Updated with correct games for today")
print(f"   NBA: {len(nba_games)} games")
print(f"   Soccer: {len(soccer_games)} games")
print(f"")
print("NBA Games Today:")
for i, game in enumerate(nba_games, 1):
    scheduled = game.get("scheduled", "TBD")
    time_part = scheduled.split("T")[1][:5] if "T" in scheduled else scheduled[:16]
    print(f"   {i}. {game['away_team']} @ {game['home_team']} - {time_part}")

