#!/usr/bin/env python3
"""Get sample basketball and soccer games for demonstration."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(UTC)
TOMORROW = TODAY + timedelta(days=1)

# Sample NBA games (typical schedule)
nba_games = [
    {
        "sport": "nba",
        "game_id": "nba_sample_1",
        "home_team": "Los Angeles Lakers",
        "away_team": "Golden State Warriors",
        "scheduled": TOMORROW.replace(hour=20, minute=0, second=0).isoformat(),
        "status": "scheduled",
        "source": "sample",
    },
    {
        "sport": "nba",
        "game_id": "nba_sample_2",
        "home_team": "Boston Celtics",
        "away_team": "Miami Heat",
        "scheduled": TOMORROW.replace(hour=19, minute=30, second=0).isoformat(),
        "status": "scheduled",
        "source": "sample",
    },
    {
        "sport": "nba",
        "game_id": "nba_sample_3",
        "home_team": "Phoenix Suns",
        "away_team": "Denver Nuggets",
        "scheduled": TOMORROW.replace(hour=22, minute=0, second=0).isoformat(),
        "status": "scheduled",
        "source": "sample",
    },
]

# Sample soccer games
soccer_games = [
    {
        "sport": "soccer",
        "game_id": "soccer_sample_1",
        "home_team": "Manchester United",
        "away_team": "Liverpool",
        "scheduled": TOMORROW.replace(hour=15, minute=0, second=0).isoformat(),
        "status": "scheduled",
        "league": "EPL",
        "source": "sample",
    },
    {
        "sport": "soccer",
        "game_id": "soccer_sample_2",
        "home_team": "Barcelona",
        "away_team": "Real Madrid",
        "scheduled": TOMORROW.replace(hour=17, minute=30, second=0).isoformat(),
        "status": "scheduled",
        "league": "La Liga",
        "source": "sample",
    },
    {
        "sport": "soccer",
        "game_id": "soccer_sample_3",
        "home_team": "Bayern Munich",
        "away_team": "Borussia Dortmund",
        "scheduled": TOMORROW.replace(hour=14, minute=30, second=0).isoformat(),
        "status": "scheduled",
        "league": "Bundesliga",
        "source": "sample",
    },
    {
        "sport": "soccer",
        "game_id": "soccer_sample_4",
        "home_team": "Inter Milan",
        "away_team": "AC Milan",
        "scheduled": TOMORROW.replace(hour=16, minute=0, second=0).isoformat(),
        "status": "scheduled",
        "league": "Serie A",
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
    "note": "Sample games for demonstration - system will process these through analytics pipeline",
}

output_file.write_text(json.dumps(payload, indent=2))

print(f"✅ Created {len(all_games)} sample games")
print(f"   NBA: {len(nba_games)}")
print(f"   Soccer: {len(soccer_games)}")
print("")
print("Sample games:")
for i, game in enumerate(all_games[:5], 1):
    scheduled = game.get("scheduled", "TBD")
    time_part = scheduled.split("T")[1][:5] if "T" in scheduled else scheduled[:16]
    print(
        f"   {i}. {game['sport'].upper()}: {game['away_team']} @ {game['home_team']} - {time_part}"
    )
