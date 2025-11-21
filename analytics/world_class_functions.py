#!/usr/bin/env python3
"""
World-Class Prediction Functions - All Advanced Factors
========================================================

Functions for calculating all predictive factors:
- Momentum & recent form
- Head-to-head matchups
- Travel & time zone impact
- Schedule strength
- Market odds & line movement
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

LOGGER = logging.getLogger(__name__)

# Team city/timezone database (simplified - expand as needed)
TEAM_CITIES: dict[str, dict[str, Any]] = {
    # NBA
    "Los Angeles Lakers": {
        "city": "Los Angeles",
        "timezone": "PST",
        "lat": 34.0522,
        "lon": -118.2437,
    },
    "LA Clippers": {"city": "Los Angeles", "timezone": "PST", "lat": 34.0522, "lon": -118.2437},
    "Boston Celtics": {"city": "Boston", "timezone": "EST", "lat": 42.3601, "lon": -71.0589},
    "New York Knicks": {"city": "New York", "timezone": "EST", "lat": 40.7128, "lon": -74.0060},
    "Miami Heat": {"city": "Miami", "timezone": "EST", "lat": 25.7617, "lon": -80.1918},
    "Chicago Bulls": {"city": "Chicago", "timezone": "CST", "lat": 41.8781, "lon": -87.6298},
    "Dallas Mavericks": {"city": "Dallas", "timezone": "CST", "lat": 32.7767, "lon": -96.7970},
    # Add more as needed...
}

# Timezone offsets from UTC
TZ_OFFSETS = {
    "EST": -5,
    "CST": -6,
    "MST": -7,
    "PST": -8,
    "EDT": -4,
    "CDT": -5,
    "MDT": -6,
    "PDT": -7,
}


def fetch_team_momentum(
    team_name: str,
    sport: str,
    recent_games: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Calculate team momentum and recent form.

    Returns:
        - win_streak: Current win streak (negative = loss streak)
        - last_5_win_pct: Win percentage in last 5 games
        - last_10_win_pct: Win percentage in last 10 games
        - point_diff_trend: Average point differential trend
        - momentum_score: Combined momentum score (-1.0 to 1.0)
    """
    if not recent_games:
        return {
            "win_streak": 0,
            "last_5_win_pct": 0.5,
            "last_10_win_pct": 0.5,
            "point_diff_trend": 0.0,
            "momentum_score": 0.0,
        }

    # Calculate win streak (most recent first)
    win_streak = 0
    for game in reversed(recent_games):
        team_won = False
        if game.get("home_team") == team_name:
            team_won = game.get("home_score", 0) > game.get("away_score", 0)
        elif game.get("away_team") == team_name:
            team_won = game.get("away_score", 0) > game.get("home_score", 0)

        if win_streak == 0:
            win_streak = 1 if team_won else -1
        elif (win_streak > 0 and team_won) or (win_streak < 0 and not team_won):
            win_streak += 1 if team_won else -1
        else:
            break

    # Calculate win percentages
    last_5 = recent_games[-5:] if len(recent_games) >= 5 else recent_games
    last_10 = recent_games[-10:] if len(recent_games) >= 10 else recent_games

    def calc_win_pct(games, team):
        if not games:
            return 0.5
        wins = 0
        for game in games:
            if game.get("home_team") == team:
                if game.get("home_score", 0) > game.get("away_score", 0):
                    wins += 1
            elif game.get("away_team") == team:
                if game.get("away_score", 0) > game.get("home_score", 0):
                    wins += 1
        return wins / len(games)

    last_5_win_pct = calc_win_pct(last_5, team_name)
    last_10_win_pct = calc_win_pct(last_10, team_name)

    # Point differential trend
    point_diffs = []
    for game in recent_games[-5:]:
        if game.get("home_team") == team_name:
            diff = game.get("home_score", 0) - game.get("away_score", 0)
        elif game.get("away_team") == team_name:
            diff = game.get("away_score", 0) - game.get("home_score", 0)
        else:
            continue
        point_diffs.append(diff)

    point_diff_trend = sum(point_diffs) / len(point_diffs) if point_diffs else 0.0

    # Momentum score: -1.0 (terrible) to 1.0 (excellent)
    momentum_score = (
        (last_5_win_pct - 0.5) * 0.4  # Recent form
        + (last_10_win_pct - 0.5) * 0.2  # Medium-term form
        + (win_streak / 10.0) * 0.3  # Streak impact
        + min(point_diff_trend / 20.0, 1.0) * 0.1  # Point differential
    )
    momentum_score = max(-1.0, min(1.0, momentum_score))

    return {
        "win_streak": win_streak,
        "last_5_win_pct": last_5_win_pct,
        "last_10_win_pct": last_10_win_pct,
        "point_diff_trend": point_diff_trend,
        "momentum_score": momentum_score,
    }


def calculate_head_to_head(
    home_team: str,
    away_team: str,
    historical_games: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Calculate head-to-head matchup history.

    Returns:
        - h2h_win_pct: Home team's H2H win percentage
        - last_10_home_wins: Home team wins in last 10 meetings
        - h2h_adjustment: Elo adjustment based on H2H (-50 to +50)
    """
    if not historical_games:
        return {
            "h2h_win_pct": 0.5,
            "last_10_home_wins": 5,
            "h2h_adjustment": 0.0,
        }

    # Filter H2H games
    h2h_games = [
        g
        for g in historical_games
        if (
            (g.get("home_team") == home_team and g.get("away_team") == away_team)
            or (g.get("home_team") == away_team and g.get("away_team") == home_team)
        )
    ]

    if not h2h_games:
        return {
            "h2h_win_pct": 0.5,
            "last_10_home_wins": 5,
            "h2h_adjustment": 0.0,
        }

    # Get last 10 meetings
    last_10 = h2h_games[-10:] if len(h2h_games) >= 10 else h2h_games

    home_wins = 0
    for game in last_10:
        if game.get("home_team") == home_team:
            if game.get("home_score", 0) > game.get("away_score", 0):
                home_wins += 1
        elif game.get("home_team") == away_team:
            if game.get("away_score", 0) > game.get("home_score", 0):
                home_wins += 1

    h2h_win_pct = home_wins / len(last_10) if last_10 else 0.5

    # Elo adjustment: +50 if 80%+ win rate, -50 if <20%, linear in between
    if h2h_win_pct >= 0.8:
        h2h_adjustment = 50.0
    elif h2h_win_pct <= 0.2:
        h2h_adjustment = -50.0
    else:
        h2h_adjustment = (h2h_win_pct - 0.5) * 100.0

    return {
        "h2h_win_pct": h2h_win_pct,
        "last_10_home_wins": home_wins,
        "h2h_adjustment": h2h_adjustment,
    }


def calculate_travel_impact(
    home_team: str,
    away_team: str,
    game_time: str | None = None,
) -> dict[str, Any]:
    """
    Calculate travel distance and time zone impact for away team.

    Returns:
        - travel_distance: Distance in miles
        - timezone_change: Hours of timezone difference
        - travel_penalty: Elo penalty for travel (-50 to 0)
    """
    home_city = TEAM_CITIES.get(home_team, {})
    away_city = TEAM_CITIES.get(away_team, {})

    if not home_city or not away_city:
        # Default: assume some travel
        return {
            "travel_distance": 1000,
            "timezone_change": 0,
            "travel_penalty": -25.0,
        }

    # Calculate distance (Haversine formula simplified)
    def haversine_distance(lat1, lon1, lat2, lon2):
        from math import atan2, cos, radians, sin, sqrt

        R = 3959  # Earth radius in miles
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    travel_distance = haversine_distance(
        away_city.get("lat", 0),
        away_city.get("lon", 0),
        home_city.get("lat", 0),
        home_city.get("lon", 0),
    )

    # Timezone change
    away_tz = away_city.get("timezone", "EST")
    home_tz = home_city.get("timezone", "EST")
    away_offset = TZ_OFFSETS.get(away_tz, -5)
    home_offset = TZ_OFFSETS.get(home_tz, -5)
    timezone_change = abs(home_offset - away_offset)

    # Travel penalty
    travel_penalty = 0.0
    if travel_distance > 1500:
        travel_penalty -= 50.0  # Long distance
    elif travel_distance > 1000:
        travel_penalty -= 30.0
    elif travel_distance > 500:
        travel_penalty -= 15.0

    if timezone_change >= 3:
        travel_penalty -= 25.0  # Major timezone change
    elif timezone_change >= 2:
        travel_penalty -= 15.0
    elif timezone_change >= 1:
        travel_penalty -= 5.0

    return {
        "travel_distance": travel_distance,
        "timezone_change": timezone_change,
        "travel_penalty": travel_penalty,
    }


def calculate_schedule_strength(
    team_name: str,
    recent_games: list[dict[str, Any]] | None = None,
    team_elos: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Calculate strength of schedule for recent games.

    Returns:
        - avg_opponent_elo: Average Elo of recent opponents
        - schedule_strength_score: Normalized strength (-1.0 to 1.0)
        - sos_adjustment: Elo adjustment for schedule bias (-30 to +30)
    """
    if not recent_games or not team_elos:
        return {
            "avg_opponent_elo": 1500.0,
            "schedule_strength_score": 0.0,
            "sos_adjustment": 0.0,
        }

    # Get last 5 opponents
    opponents = []
    for game in recent_games[-5:]:
        if game.get("home_team") == team_name:
            opp = game.get("away_team")
        elif game.get("away_team") == team_name:
            opp = game.get("home_team")
        else:
            continue
        if opp:
            opponents.append(opp)

    if not opponents:
        return {
            "avg_opponent_elo": 1500.0,
            "schedule_strength_score": 0.0,
            "sos_adjustment": 0.0,
        }

    opponent_elos = [team_elos.get(opp, 1500.0) for opp in opponents]
    avg_opponent_elo = sum(opponent_elos) / len(opponent_elos)

    # Normalize: 1400 = weak (-1.0), 1600 = strong (+1.0)
    schedule_strength_score = (avg_opponent_elo - 1500.0) / 100.0
    schedule_strength_score = max(-1.0, min(1.0, schedule_strength_score))

    # Adjustment: if playing weak opponents, stats are inflated (lower Elo)
    sos_adjustment = -schedule_strength_score * 30.0

    return {
        "avg_opponent_elo": avg_opponent_elo,
        "schedule_strength_score": schedule_strength_score,
        "sos_adjustment": sos_adjustment,
    }


def fetch_market_odds(game_id: str, sport: str) -> dict[str, Any] | None:
    """
    Fetch market odds from free sources (ESPN implied odds or scraping).

    Returns:
        - home_prob: Market implied home win probability
        - away_prob: Market implied away win probability
        - line_movement: Movement since opening
        - sharp_signal: "fade", "back", or "neutral"
    """
    # ESPN scoreboard may have implied odds
    # This is a placeholder - expand based on available free sources
    return None


__all__ = [
    "fetch_team_momentum",
    "calculate_head_to_head",
    "calculate_travel_impact",
    "calculate_schedule_strength",
    "fetch_market_odds",
]
