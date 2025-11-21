#!/usr/bin/env python3
"""Advanced sports analytics features: Elo ratings, injuries, weather, rest days.

This module provides world-class feature engineering components:
- Elo rating system for dynamic team strength
- NBA injury report integration via API-NBA
- Weather data for outdoor sports (NFL, MLB)
- Rest days and back-to-back game fatigue analysis
- Referee bias tracking
- Home court advantage metrics
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

ROOT = Path(os.path.expanduser("~/neolight"))
DATA = ROOT / "data"
ELO_DIR = DATA / "sports_elo"
INJURIES_DIR = DATA / "sports_injuries"

for directory in (ELO_DIR, INJURIES_DIR):
    directory.mkdir(parents=True, exist_ok=True)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Elo rating constants
K_FACTOR = 32  # How quickly ratings change
HOME_ADVANTAGE = 100  # Elo points for home team
INITIAL_ELO = 1500  # Starting rating for new teams


class EloRatingSystem:
    """Dynamic team strength ratings using Elo algorithm."""

    def __init__(self, sport: str, k_factor: float = K_FACTOR):
        self.sport = sport
        self.k_factor = k_factor
        self.ratings: dict[str, float] = defaultdict(lambda: INITIAL_ELO)
        self.history: dict[str, list[tuple[str, float]]] = defaultdict(list)  # (date, rating)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected win probability for team A."""
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def update_ratings(
        self,
        team_a: str,
        team_b: str,
        score_a: int,
        score_b: int,
        is_home_a: bool = True,
        date: str = "",
    ) -> dict[str, float]:
        """
        Update Elo ratings after a game.

        Args:
            team_a: First team name
            team_b: Second team name
            score_a: Team A score
            score_b: Team B score
            is_home_a: Whether team A is home
            date: Game date for history tracking

        Returns:
            Dict with new ratings: {team_a: new_rating_a, team_b: new_rating_b}
        """
        rating_a = self.ratings[team_a]
        rating_b = self.ratings[team_b]

        # Apply home advantage
        if is_home_a:
            rating_a_adj = rating_a + HOME_ADVANTAGE
            rating_b_adj = rating_b
        else:
            rating_a_adj = rating_a
            rating_b_adj = rating_b + HOME_ADVANTAGE

        # Expected scores
        expected_a = self.expected_score(rating_a_adj, rating_b_adj)
        expected_b = 1.0 - expected_a

        # Actual result (1=win, 0.5=tie, 0=loss)
        if score_a > score_b:
            actual_a, actual_b = 1.0, 0.0
        elif score_a < score_b:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.5, 0.5

        # Margin of victory multiplier (for blowouts)
        margin = abs(score_a - score_b)
        mov_multiplier = 1.0 + (margin / 10.0) if margin > 10 else 1.0

        # Update ratings
        delta_a = self.k_factor * mov_multiplier * (actual_a - expected_a)
        delta_b = self.k_factor * mov_multiplier * (actual_b - expected_b)

        new_rating_a = rating_a + delta_a
        new_rating_b = rating_b + delta_b

        self.ratings[team_a] = new_rating_a
        self.ratings[team_b] = new_rating_b

        # Track history
        if date:
            self.history[team_a].append((date, new_rating_a))
            self.history[team_b].append((date, new_rating_b))

        return {team_a: new_rating_a, team_b: new_rating_b}

    def get_rating(self, team: str) -> float:
        """Get current Elo rating for a team."""
        return self.ratings[team]

    def get_matchup_probability(self, home_team: str, away_team: str) -> dict[str, float]:
        """Calculate win probabilities for a matchup."""
        home_rating = self.ratings[home_team] + HOME_ADVANTAGE
        away_rating = self.ratings[away_team]

        home_prob = self.expected_score(home_rating, away_rating)
        away_prob = 1.0 - home_prob

        return {
            "home_win_prob": home_prob,
            "away_win_prob": away_prob,
            "home_elo": self.ratings[home_team],
            "away_elo": self.ratings[away_team],
        }

    def save(self, path: Path | None = None) -> None:
        """Save Elo ratings to disk."""
        if path is None:
            path = ELO_DIR / f"{self.sport}_elo.json"

        data = {
            "sport": self.sport,
            "k_factor": self.k_factor,
            "ratings": dict(self.ratings),
            "history": {
                team: [(date, rating) for date, rating in hist]
                for team, hist in self.history.items()
            },
            "updated_at": datetime.now(UTC).isoformat(),
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, sport: str, path: Path | None = None) -> EloRatingSystem:
        """Load Elo ratings from disk."""
        if path is None:
            path = ELO_DIR / f"{sport}_elo.json"

        if not path.exists():
            return cls(sport)

        data = json.loads(path.read_text())
        system = cls(sport, k_factor=data.get("k_factor", K_FACTOR))
        system.ratings = defaultdict(lambda: INITIAL_ELO, data.get("ratings", {}))

        history_data = data.get("history", {})
        for team, hist in history_data.items():
            system.history[team] = [(date, rating) for date, rating in hist]

        return system


class InjuryTracker:
    """Track player injuries from API-NBA (and other sports when available)."""

    def __init__(self, rapidapi_key: str):
        if not rapidapi_key:
            raise ValueError("RAPIDAPI_KEY required for injury tracking")
        self.rapidapi_key = rapidapi_key

    def fetch_nba_injuries(self) -> list[dict[str, Any]]:
        """Fetch current NBA injury reports from API-NBA."""
        if requests is None:
            print("[injuries] requests library not available", flush=True)
            return []

        try:
            url = "https://api-nba-v1.p.rapidapi.com/injuries"
            headers = {
                "x-rapidapi-host": "api-nba-v1.p.rapidapi.com",
                "x-rapidapi-key": self.rapidapi_key,
            }

            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"[injuries] API-NBA request failed: {response.status_code}", flush=True)
                return []

            data = response.json()
            injuries = data.get("response", [])
            return injuries

        except Exception as exc:  # pragma: no cover
            print(f"[injuries] Error fetching NBA injuries: {exc}", flush=True)
            return []

    def get_team_injury_impact(
        self, team_name: str, injuries: list[dict[str, Any]] | None = None
    ) -> float:
        """
        Calculate injury impact score for a team (0.0 = no impact, 1.0 = heavy impact).

        Returns a normalized score based on number and severity of injuries.
        """
        if injuries is None:
            injuries = self.fetch_nba_injuries()

        team_injuries = [
            inj
            for inj in injuries
            if inj.get("team", {}).get("name", "").lower() == team_name.lower()
        ]

        if not team_injuries:
            return 0.0

        # Simple heuristic: count injuries and weigh by status
        impact = 0.0
        for injury in team_injuries:
            status = (injury.get("status") or "").lower()
            if "out" in status:
                impact += 1.0
            elif "doubtful" in status:
                impact += 0.7
            elif "questionable" in status:
                impact += 0.3

        # Normalize to 0-1 range (assume max 5 key injuries = full impact)
        return min(impact / 5.0, 1.0)


def calculate_rest_days(games: list[dict[str, Any]], team: str, current_date: str) -> int:
    """
    Calculate days of rest for a team before a game.

    Args:
        games: Historical game records (sorted by date)
        team: Team name
        current_date: Date of upcoming game (ISO format)

    Returns:
        Number of rest days (0 = back-to-back, 1+ = rest days)
    """
    try:
        current_dt = datetime.fromisoformat(current_date.replace("Z", "+00:00"))
    except ValueError:
        return 3  # Default to normal rest

    # Find last game for this team
    team_games = [g for g in games if team in [g.get("home_team"), g.get("away_team")]]
    team_games.sort(key=lambda g: g.get("scheduled", ""))

    for game in reversed(team_games):
        try:
            game_date = datetime.fromisoformat(game.get("scheduled", "").replace("Z", "+00:00"))
            if game_date < current_dt:
                rest_days = (current_dt - game_date).days
                return max(0, rest_days)
        except ValueError:
            continue

    return 3  # Default if no previous game found


def fetch_weather_data(location: str, date: str) -> dict[str, Any]:
    """
    Fetch weather data for outdoor sports (NFL, MLB).

    Note: Requires a weather API key. Placeholder for now.
    Returns mock data - integrate with OpenWeather or WeatherAPI when ready.
    """
    # TODO: Integrate real weather API when budget allows
    return {
        "temperature": 65,
        "precipitation": 0.0,
        "wind_speed": 5,
        "conditions": "clear",
        "is_dome": False,
    }


def calculate_home_advantage_score(
    team: str, venue: str, historical_home_record: dict[str, int] | None = None
) -> float:
    """
    Calculate home advantage score (0.0 = no advantage, 1.0 = strong advantage).

    Args:
        team: Team name
        venue: Venue name
        historical_home_record: Optional dict with {wins, losses} at home

    Returns:
        Home advantage score
    """
    if historical_home_record:
        wins = historical_home_record.get("wins", 0)
        losses = historical_home_record.get("losses", 0)
        total = wins + losses
        if total > 10:
            win_pct = wins / total
            # Normalize: 0.50 = neutral (0.5), 0.70+ = strong (1.0)
            return min((win_pct - 0.5) / 0.2, 1.0)

    # Default home advantage
    return 0.6


# Closing Line Value (CLV) calculator
def calculate_clv(bet_odds: float, closing_odds: float) -> float:
    """
    Calculate Closing Line Value (CLV) - how much better your line was vs. closing.

    Positive CLV = you beat the market (good!)
    Negative CLV = market moved against you (bad)

    Args:
        bet_odds: Odds when you placed bet (American or Decimal)
        closing_odds: Odds at game start (closing line)

    Returns:
        CLV percentage
    """

    # Convert American odds to implied probability
    def american_to_prob(odds: float) -> float:
        if odds > 0:
            return 100.0 / (odds + 100.0)
        else:
            return -odds / (-odds + 100.0)

    bet_prob = american_to_prob(bet_odds)
    closing_prob = american_to_prob(closing_odds)

    # CLV = (closing implied prob - bet implied prob) / bet implied prob
    clv = (closing_prob - bet_prob) / bet_prob if bet_prob > 0 else 0.0
    return clv * 100  # Return as percentage
