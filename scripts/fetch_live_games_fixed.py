#!/usr/bin/env python3
"""Fetch today's live basketball and soccer games using multiple API sources."""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "f89c81c096msh0e367842c4a9cedp172050jsn8f96a4f06504")
SPORTRADAR_KEY = os.getenv("SPORTRADAR_API_KEY", "")
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TOMORROW = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")


def fetch_nba_games_rapidapi():
    """Fetch NBA games using RapidAPI multiple endpoints."""
    games = []
    
    # Try multiple RapidAPI endpoints
    endpoints = [
        {
            "url": "https://api-nba-v1.p.rapidapi.com/games",
            "host": "api-nba-v1.p.rapidapi.com",
            "params": {"date": TODAY.replace("-", "")},
        },
        {
            "url": "https://odds-api1.p.rapidapi.com/fixtures/basketball_nba",
            "host": "odds-api1.p.rapidapi.com",
            "params": {"date": TODAY},
        },
        {
            "url": "https://api-basketball.p.rapidapi.com/games",
            "host": "api-basketball.p.rapidapi.com",
            "params": {"date": TODAY},
        },
    ]
    
    for endpoint in endpoints:
        try:
            headers = {
                "x-rapidapi-host": endpoint["host"],
                "x-rapidapi-key": RAPIDAPI_KEY,
            }
            
            response = requests.get(
                endpoint["url"], headers=headers, params=endpoint["params"], timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse different response formats
                if "response" in data:
                    # NBA API format
                    for game in data["response"]:
                        if game.get("date", {}).get("start", "").startswith(TODAY):
                            home = game.get("teams", {}).get("home", {}).get("name", "")
                            away = game.get("teams", {}).get("visitors", {}).get("name", "")
                            game_id = str(game.get("id", ""))
                            scheduled = game.get("date", {}).get("start", "")
                            
                            games.append({
                                "sport": "nba",
                                "game_id": f"nba_{game_id}",
                                "home_team": home,
                                "away_team": away,
                                "scheduled": scheduled,
                                "status": "scheduled",
                                "source": endpoint["host"],
                            })
                
                elif "data" in data:
                    # Odds API format
                    for fix in data["data"]:
                        commence_time = fix.get("commence_time", "")
                        if TODAY in commence_time:
                            games.append({
                                "sport": "nba",
                                "game_id": fix.get("id", ""),
                                "home_team": fix.get("home_team", ""),
                                "away_team": fix.get("away_team", ""),
                                "scheduled": commence_time,
                                "status": "scheduled",
                                "source": endpoint["host"],
                            })
                
                if games:
                    print(f"✅ Found {len(games)} NBA games via {endpoint['host']}")
                    break
                    
        except Exception as e:
            continue
    
    return games


def fetch_soccer_games_rapidapi():
    """Fetch soccer games using RapidAPI multiple endpoints."""
    games = []
    
    # Try multiple RapidAPI endpoints
    endpoints = [
        {
            "url": "https://odds-api1.p.rapidapi.com/fixtures/soccer_epl",
            "host": "odds-api1.p.rapidapi.com",
            "params": {"date": TODAY},
        },
        {
            "url": "https://odds-api1.p.rapidapi.com/fixtures/soccer",
            "host": "odds-api1.p.rapidapi.com",
            "params": {"date": TODAY},
        },
        {
            "url": "https://api-football-v1.p.rapidapi.com/v3/fixtures",
            "host": "api-football-v1.p.rapidapi.com",
            "params": {"date": TODAY},
        },
    ]
    
    leagues = ["soccer_epl", "soccer_la_liga", "soccer_serie_a", "soccer_bundesliga", "soccer_ligue_1"]
    
    for league in leagues:
        try:
            url = f"https://odds-api1.p.rapidapi.com/fixtures/{league}"
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
                        # Avoid duplicates
                        game_id = fix.get("id", "")
                        if not any(g.get("game_id") == game_id for g in games):
                            games.append({
                                "sport": "soccer",
                                "game_id": game_id,
                                "home_team": fix.get("home_team", ""),
                                "away_team": fix.get("away_team", ""),
                                "scheduled": commence_time,
                                "status": "scheduled",
                                "league": league,
                                "source": "odds-api1",
                            })
        except Exception as e:
            continue
    
    if games:
        print(f"✅ Found {len(games)} soccer games")
    
    return games


def save_games(games):
    """Save games to state file."""
    output_file = STATE / "today_games.json"
    payload = {
        "date": TODAY,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "games": games,
        "count": len(games),
        "nba_count": len([g for g in games if g["sport"] == "nba"]),
        "soccer_count": len([g for g in games if g["sport"] == "soccer"]),
    }
    output_file.write_text(json.dumps(payload, indent=2))
    return output_file


def main():
    print(f"🏀⚽ Fetching Live Games for Today ({TODAY})")
    print("=" * 60)
    print("")
    
    all_games = []
    
    # Fetch NBA games
    print("1. Fetching NBA games...")
    nba_games = fetch_nba_games_rapidapi()
    all_games.extend(nba_games)
    print(f"   Found: {len(nba_games)} NBA games")
    
    # Fetch soccer games
    print("")
    print("2. Fetching soccer games...")
    soccer_games = fetch_soccer_games_rapidapi()
    all_games.extend(soccer_games)
    print(f"   Found: {len(soccer_games)} soccer games")
    
    # Save games
    print("")
    print("3. Saving games...")
    if all_games:
        save_games(all_games)
        print(f"✅ Saved {len(all_games)} games total")
        print(f"   NBA: {len(nba_games)} | Soccer: {len(soccer_games)}")
        print("")
        print("Sample games:")
        for i, game in enumerate(all_games[:10], 1):
            scheduled = game.get("scheduled", "TBD")
            time_part = scheduled.split("T")[1][:5] if "T" in scheduled else scheduled[:16]
            print(f"   {i}. {game['sport'].upper()}: {game['away_team']} @ {game['home_team']} - {time_part}")
    else:
        print("⚠️ No games found for today")
        # Create empty file for processing
        save_games([])
    
    return all_games


if __name__ == "__main__":
    main()








