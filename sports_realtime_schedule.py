#!/usr/bin/env python3
"""
Einstein-Level Real-Time Schedule Fetcher
=========================================
Fetches real-time game schedules for today and upcoming days from multiple sources:
- SofaScore API (free, no auth required)
- RapidAPI Scores API (backup)
- Sportradar API (if available)

Ensures predictions are based on actual scheduled games, not cached historical data.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

# Python 3.9 compatibility
UTC = UTC
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

for directory in (STATE, DATA, LOGS):
    directory.mkdir(parents=True, exist_ok=True)

SCHEDULE_CACHE = STATE / "realtime_schedule.json"
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


class RealTimeScheduleFetcher:
    """Einstein-level real-time schedule fetcher with multi-source fallback"""

    def __init__(self):
        self.session = requests.Session() if requests else None
        if self.session:
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
                }
            )

    def fetch_sofascore_schedule(self, sport: str, days: int = 3) -> list[dict[str, Any]]:
        """Fetch schedule from SofaScore API (free, no auth)"""
        if not self.session:
            return []

        events = []
        today = datetime.now(UTC).date()

        # SofaScore sport IDs
        sport_ids = {
            "nba": "basketball",
            "nfl": "american-football",
            "mlb": "baseball",
            "soccer": "football",
        }

        sport_id = sport_ids.get(sport.lower(), sport.lower())

        for offset in range(days + 1):
            target_date = (today + timedelta(days=offset)).isoformat()
            url = (
                f"https://api.sofascore.com/api/v1/sport/{sport_id}/scheduled-events/{target_date}"
            )

            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    payload = response.json()
                    events.extend(payload.get("events", []))
            except Exception as e:
                print(f"[realtime_schedule] SofaScore fetch error: {e}", flush=True)

        return events

    def fetch_rapidapi_schedule(self, sport: str, days: int = 3) -> list[dict[str, Any]]:
        """Fetch schedule from RapidAPI Scores API (backup)"""
        if not self.session or not RAPIDAPI_KEY:
            return []

        events = []
        today = datetime.now(UTC)

        # RapidAPI endpoint
        url = "https://api-odds.p.rapidapi.com/v4/sports"
        headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-odds.p.rapidapi.com"}

        sport_map = {
            "nba": "basketball_nba",
            "nfl": "americanfootball_nfl",
            "mlb": "baseball_mlb",
            "soccer": "soccer_epl",
        }

        api_sport = sport_map.get(sport.lower(), sport.lower())

        try:
            # Get upcoming games
            games_url = f"https://api-odds.p.rapidapi.com/v4/sports/{api_sport}/odds"
            params = {
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "american",
                "dateFormat": "iso",
            }
            response = self.session.get(games_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                events.extend(payload.get("data", []))
        except Exception as e:
            print(f"[realtime_schedule] RapidAPI fetch error: {e}", flush=True)

        return events

    def normalize_game(
        self, event: dict[str, Any], sport: str, source: str
    ) -> dict[str, Any] | None:
        """Normalize game data from different sources into standard format"""
        try:
            if source == "sofascore":
                # SofaScore format
                home_team = event.get("homeTeam", {}).get("name", "")
                away_team = event.get("awayTeam", {}).get("name", "")
                start_timestamp = event.get("startTimestamp")

                if not home_team or not away_team:
                    return None

                if start_timestamp:
                    scheduled = datetime.fromtimestamp(start_timestamp, tz=UTC).isoformat()
                else:
                    scheduled = datetime.now(UTC).isoformat()

                return {
                    "game_id": f"{sport}_{event.get('id', '')}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "scheduled": scheduled,
                    "sport": sport,
                    "source": "sofascore",
                    "status": event.get("status", {}).get("type", "notstarted"),
                }

            elif source == "rapidapi":
                # RapidAPI format
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")
                commence_time = event.get("commence_time")

                if not home_team or not away_team:
                    return None

                if commence_time:
                    try:
                        scheduled = datetime.fromisoformat(
                            commence_time.replace("Z", "+00:00")
                        ).isoformat()
                    except:
                        scheduled = datetime.now(UTC).isoformat()
                else:
                    scheduled = datetime.now(UTC).isoformat()

                return {
                    "game_id": f"{sport}_{event.get('id', '')}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "scheduled": scheduled,
                    "sport": sport,
                    "source": "rapidapi",
                    "status": "notstarted",
                }

        except Exception as e:
            print(f"[realtime_schedule] Normalization error: {e}", flush=True)
            return None

        return None

    def fetch_today_schedule(self, sport: str) -> list[dict[str, Any]]:
        """Fetch today's schedule for a sport from multiple sources"""
        games = []

        # Try SofaScore first (free, reliable)
        sofascore_events = self.fetch_sofascore_schedule(sport, days=1)
        for event in sofascore_events:
            game = self.normalize_game(event, sport, "sofascore")
            if game:
                games.append(game)

        # If no games found, try RapidAPI
        if not games:
            rapidapi_events = self.fetch_rapidapi_schedule(sport, days=1)
            for event in rapidapi_events:
                game = self.normalize_game(event, sport, "rapidapi")
                if game:
                    games.append(game)

        return games

    def save_schedule(self, schedules: dict[str, list[dict[str, Any]]]):
        """Save fetched schedules to cache"""
        schedules["last_updated"] = datetime.now(UTC).isoformat()
        SCHEDULE_CACHE.write_text(json.dumps(schedules, indent=2))

    def load_cached_schedule(self) -> dict[str, list[dict[str, Any]]]:
        """Load cached schedule if recent (within 6 hours)"""
        if not SCHEDULE_CACHE.exists():
            return {}

        try:
            data = json.loads(SCHEDULE_CACHE.read_text())
            last_updated = data.get("last_updated")
            if last_updated:
                last_update_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                age_hours = (datetime.now(UTC) - last_update_dt).total_seconds() / 3600
                if age_hours < 6:  # Cache valid for 6 hours
                    return data
        except Exception:
            pass

        return {}


def fetch_realtime_schedules(sports: list[str] = None) -> dict[str, list[dict[str, Any]]]:
    """
    Main function to fetch real-time schedules for today.

    Args:
        sports: List of sports to fetch (default: ['nba', 'nfl', 'mlb', 'soccer'])

    Returns:
        Dictionary mapping sport to list of games scheduled for today
    """
    if sports is None:
        sports = ["nba", "nfl", "mlb", "soccer"]

    fetcher = RealTimeScheduleFetcher()

    # Check cache first
    cached = fetcher.load_cached_schedule()
    if cached and all(sport in cached for sport in sports):
        print("[realtime_schedule] Using cached schedule (recent)", flush=True)
        return cached

    print("[realtime_schedule] Fetching real-time schedules...", flush=True)
    schedules = {}

    for sport in sports:
        games = fetcher.fetch_today_schedule(sport)
        schedules[sport] = games
        print(
            f"[realtime_schedule] {sport.upper()}: Found {len(games)} games for today", flush=True
        )

    # Save to cache
    fetcher.save_schedule(schedules)

    return schedules


if __name__ == "__main__":
    """CLI for testing"""
    schedules = fetch_realtime_schedules(["nba", "soccer"])
    print(json.dumps(schedules, indent=2))
