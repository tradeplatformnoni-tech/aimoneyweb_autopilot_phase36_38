"""Utilities for sports data ingestion, historical storage, and odds fetching.

This module centralises access to Sportradar schedules/results and third-party
odds providers so that agents can request consistent data regardless of the
execution environment. It handles backfilling multi-season history (default 7
years) and storing datasets under the `data/` directory for downstream model
training and evaluation.

Environment variables used:
- SPORTRADAR_API_KEY: API key for Sportradar feeds.
- SPORTS_ODDS_API_KEY (optional): Generic odds API key (e.g., TheOddsAPI, OddsJam) when a provider requires it.
- SPORTS_ODDS_PROVIDER: Provider identifier (default: theoddsapi).

The functions are defensive (fail-fast logging) and fall back to mock data when
remote endpoints are unavailable so that development can proceed offline.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - requests should be installed in prod
    requests = None  # type: ignore

from analytics.rapidapi_scores import RapidAPIScoresClient

LOGGER = logging.getLogger(__name__)

SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY", "")
SPORTS_ODDS_API_KEY = os.getenv("SPORTS_ODDS_API_KEY", "")
SPORTS_ODDS_PROVIDER = os.getenv("SPORTS_ODDS_PROVIDER", "theoddsapi").lower()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

DATA_ROOT = Path(os.path.expanduser("~/neolight")) / "data"
HISTORY_DIR = DATA_ROOT / "sports_history"
ODDS_DIR = DATA_ROOT / "sports_odds"
SCORES_DIR = DATA_ROOT / "scores_snapshots"

SOCCER_HISTORY_LOCAL = DATA_ROOT / "sports_history" / "soccer"
SOCCER_ODDS_LOCAL = DATA_ROOT / "odds_snapshots" / "soccer"
NBA_HISTORY_LOCAL = DATA_ROOT / "sports_history" / "nba"
NBA_ODDS_LOCAL = DATA_ROOT / "odds_snapshots" / "nba"

_DEFAULT_SOCCER_LEAGUES = (
    "39,140,135,78,61,2,253"  # EPL, La Liga, Serie A, Bundesliga, Ligue1, Champions, MLS
)
SOCCER_LEAGUES = [
    league.strip()
    for league in os.getenv("SOCCER_LEAGUE_IDS", _DEFAULT_SOCCER_LEAGUES).split(",")
    if league.strip()
]


def _ensure_dirs() -> None:
    for directory in (DATA_ROOT, HISTORY_DIR, ODDS_DIR, SCORES_DIR):
        directory.mkdir(parents=True, exist_ok=True)


_ensure_dirs()


def _ensure_local_dirs() -> None:
    for directory in (SOCCER_HISTORY_LOCAL, SOCCER_ODDS_LOCAL, NBA_HISTORY_LOCAL, NBA_ODDS_LOCAL):
        directory.mkdir(parents=True, exist_ok=True)


_ensure_local_dirs()


SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY", "")
SPORTS_ODDS_API_KEY = os.getenv("SPORTS_ODDS_API_KEY", "")
SPORTS_ODDS_PROVIDER = os.getenv("SPORTS_ODDS_PROVIDER", "theoddsapi").lower()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

_DEFAULT_SOCCER_LEAGUES = (
    "39,140,135,78,61,2,253"  # EPL, La Liga, Serie A, Bundesliga, Ligue1, Champions, MLS
)
SOCCER_LEAGUES = [
    league.strip()
    for league in os.getenv("SOCCER_LEAGUE_IDS", _DEFAULT_SOCCER_LEAGUES).split(",")
    if league.strip()
]


class DataFetchError(RuntimeError):
    """Raised when required data cannot be fetched."""


@dataclass
class GameRecord:
    sport: str
    game_id: str
    season: str
    scheduled: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sport": self.sport,
            "game_id": self.game_id,
            "season": self.season,
            "scheduled": self.scheduled,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "status": self.status,
        }


@dataclass
class OddsRecord:
    sport: str
    game_id: str
    provider: str
    collected_at: str
    home_price: float | None
    away_price: float | None
    draw_price: float | None
    market: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sport": self.sport,
            "game_id": self.game_id,
            "provider": self.provider,
            "collected_at": self.collected_at,
            "home_price": self.home_price,
            "away_price": self.away_price,
            "draw_price": self.draw_price,
            "market": self.market,
        }


class SportradarClient:
    """Minimal Sportradar client for schedules and results."""

    BASE_URL = "https://api.sportradar.com"

    SPORT_PATHS = {
        "nfl": "nfl-ot2/games/{season}/REG/schedule.json",
        "nba": "nba/trial/v8/en/games/{season}/REG/schedule.json",
        "mlb": "mlb/trial/v7/en/games/{season}/schedule.json",
    }

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        if not api_key:
            raise ValueError("SPORTRADAR_API_KEY is required")
        if requests is None:
            raise ImportError("requests is required for SportradarClient")
        self.api_key = api_key
        self.timeout = timeout

    def fetch_season(self, sport: str, season: str) -> list[GameRecord]:
        sport = sport.lower()
        template = self.SPORT_PATHS.get(sport)
        if not template:
            raise ValueError(f"Unsupported sport for Sportradar fetch: {sport}")

        url = f"{self.BASE_URL}/{template.format(season=season)}?api_key={self.api_key}"
        LOGGER.debug("Fetching Sportradar season data", extra={"sport": sport, "season": season})
        response = requests.get(url, timeout=self.timeout)
        if response.status_code != 200:
            raise DataFetchError(
                f"Sportradar request failed: {response.status_code} {response.text[:200]}"
            )

        payload = response.json()
        games: list[GameRecord] = []

        if "games" in payload:
            raw_games = payload["games"]
        elif "weeks" in payload:
            raw_games = [g for week in payload.get("weeks", []) for g in week.get("games", [])]
        else:
            raw_games = []

        for game in raw_games:
            games.append(
                GameRecord(
                    sport=sport,
                    game_id=game.get("id", ""),
                    season=season,
                    scheduled=game.get("scheduled", ""),
                    home_team=(game.get("home", {}) or {}).get("name", ""),
                    away_team=(game.get("away", {}) or {}).get("name", ""),
                    home_score=self._safe_int(game.get("home_points")),
                    away_score=self._safe_int(game.get("away_points")),
                    status=game.get("status", "unknown"),
                )
            )

        return games

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


class APIFootballClient:
    """Client for API-Football (soccer) data via RapidAPI."""

    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        if not api_key:
            raise ValueError("RAPIDAPI_KEY is required for API-Football")
        if requests is None:
            raise ImportError("requests is required for APIFootballClient")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
            "x-rapidapi-key": self.api_key,
        }

    def fetch_fixtures(self, league: str, season: str) -> list[GameRecord]:
        """Fetch completed fixtures for a league and season."""
        url = f"{self.BASE_URL}/fixtures"
        params = {
            "league": league,
            "season": season,
            "status": "FT",  # Finished matches only
        }
        response = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise DataFetchError(
                f"API-Football request failed: {response.status_code} {response.text[:200]}"
            )

        payload = response.json()
        fixtures = payload.get("response", [])
        games: list[GameRecord] = []

        for item in fixtures:
            fixture = item.get("fixture", {}) or {}
            teams = item.get("teams", {}) or {}
            goals = item.get("goals", {}) or {}

            game_id = str(fixture.get("id", ""))
            scheduled = fixture.get("date", "")
            status = (fixture.get("status", {}) or {}).get("long", "unknown")
            home_team = (teams.get("home", {}) or {}).get("name", "")
            away_team = (teams.get("away", {}) or {}).get("name", "")

            home_score = self._safe_int(goals.get("home"))
            away_score = self._safe_int(goals.get("away"))

            games.append(
                GameRecord(
                    sport="soccer",
                    game_id=game_id,
                    season=season,
                    scheduled=scheduled,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                )
            )

        return games

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


class OddsProviderClient:
    """Fetch odds data from third-party providers with optional historical support."""

    def __init__(self, provider: str, api_key: str, timeout: int = 15) -> None:
        if requests is None:
            raise ImportError("requests is required for OddsProviderClient")
        if not api_key:
            raise ValueError("SPORTS_ODDS_API_KEY is required for odds provider")
        self.provider = provider
        self.api_key = api_key
        self.timeout = timeout

    def fetch_odds_snapshot(
        self,
        sport: str,
        regions: Iterable[str] = ("us",),
        markets: Iterable[str] = ("h2h", "spreads", "totals"),
    ) -> list[OddsRecord]:
        sport_key = self._provider_sport_key(sport)
        odds: list[OddsRecord] = []
        ts = datetime.now(UTC).isoformat()

        if self.provider == "theoddsapi":
            base = "https://api.the-odds-api.com/v4/sports"
            url = (
                f"{base}/{sport_key}/odds/?apiKey={self.api_key}&regions={','.join(regions)}"
                f"&markets={','.join(markets)}&oddsFormat=american"
            )
            response = requests.get(url, timeout=self.timeout)
            if response.status_code != 200:
                raise DataFetchError(
                    f"Odds API request failed: {response.status_code} {response.text[:200]}"
                )
            payload = response.json()
            for event in payload:
                game_id = event.get("id") or event.get("event_id") or ""
                for market in event.get("bookmakers", []):
                    for outcome in market.get("markets", []):
                        if outcome.get("key") not in markets:
                            continue
                        prices = outcome.get("outcomes", [])
                        home_price = self._extract_price(prices, target="home")
                        away_price = self._extract_price(prices, target="away")
                        draw_price = self._extract_price(prices, target="draw")
                        odds.append(
                            OddsRecord(
                                sport=sport,
                                game_id=game_id,
                                provider=self.provider,
                                collected_at=ts,
                                home_price=home_price,
                                away_price=away_price,
                                draw_price=draw_price,
                                market=outcome.get("key", "unknown"),
                            )
                        )
        elif self.provider == "rapidapi":
            # RapidAPI ODDS-API integration
            url = f"https://odds-api1.p.rapidapi.com/fixtures/{sport_key}"
            headers = {
                "x-rapidapi-host": "odds-api1.p.rapidapi.com",
                "x-rapidapi-key": self.api_key,
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                LOGGER.warning(
                    f"RapidAPI odds request failed: {response.status_code}", extra={"sport": sport}
                )
                return odds  # Return empty list instead of raising

            payload = response.json()
            events = payload.get("data", []) if isinstance(payload, dict) else []

            for event in events:
                game_id = event.get("id", "") or event.get("fixtureId", "")
                bookmakers = event.get("odds", {}).get("bookmakers", [])

                for bookmaker in bookmakers:
                    markets_data = bookmaker.get("markets", [])
                    for market_data in markets_data:
                        market_type = market_data.get("key", "h2h")
                        outcomes = market_data.get("outcomes", [])

                        home_price = None
                        away_price = None
                        draw_price = None

                        for outcome in outcomes:
                            name = (outcome.get("name") or "").lower()
                            price = outcome.get("price") or outcome.get("odds")
                            if "home" in name:
                                home_price = self._safe_float(price)
                            elif "away" in name:
                                away_price = self._safe_float(price)
                            elif "draw" in name or "tie" in name:
                                draw_price = self._safe_float(price)

                        odds.append(
                            OddsRecord(
                                sport=sport,
                                game_id=game_id,
                                provider="rapidapi",
                                collected_at=ts,
                                home_price=home_price,
                                away_price=away_price,
                                draw_price=draw_price,
                                market=market_type,
                            )
                        )
        else:
            raise ValueError(f"Unsupported odds provider: {self.provider}")

        return odds

    def _provider_sport_key(self, sport: str) -> str:
        lookup = {
            "nfl": "americanfootball_nfl",
            "nba": "basketball_nba",
            "mlb": "baseball_mlb",
        }
        return lookup.get(sport.lower(), sport.lower())

    @staticmethod
    def _extract_price(outcomes: Iterable[dict[str, Any]], target: str) -> float | None:
        for outcome in outcomes:
            name = (outcome.get("name") or "").lower()
            if target in name:
                try:
                    return float(outcome.get("price"))
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def persist_records(records: Iterable[dict[str, Any]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as f:
        json.dump(list(records), f, indent=2)


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - guard against corrupted json
        LOGGER.warning("Failed to load JSON data", extra={"path": str(path), "error": str(exc)})
        return []


def backfill_sportradar_history(sport: str, seasons: Iterable[str]) -> list[GameRecord]:
    """Fetch and persist multi-season game history for a sport."""

    sport_key = sport.lower()
    if sport_key == "soccer":
        records = load_local_soccer_history()
        if records:
            LOGGER.info("Loaded %s soccer games from local cache", len(records))
            return records
        LOGGER.warning("Local soccer history empty; run analytics.soccer_ingest.run_full_ingestion")
        return []

    if sport_key == "nba":
        records = load_local_nba_history()
        if records:
            LOGGER.info("Loaded %s NBA games from local cache", len(records))
            return records
        LOGGER.warning("Local NBA history empty; run analytics.nba_ingest.run_full_ingestion")
        # fall through to API if configured

    if not SPORTRADAR_API_KEY:
        LOGGER.warning("SPORTRADAR_API_KEY missing; returning cached history if available")
        history_files = [HISTORY_DIR / sport / f"{season}.json" for season in seasons]
        games: list[GameRecord] = []
        for path in history_files:
            cached = load_records(path)
            for item in cached:
                games.append(GameRecord(**item))
        return games

    client = SportradarClient(SPORTRADAR_API_KEY)
    all_games: list[GameRecord] = []

    for season in seasons:
        try:
            games = client.fetch_season(sport, season)
            if not games:
                LOGGER.warning(
                    "No games returned for season", extra={"sport": sport, "season": season}
                )
                continue
            dest = HISTORY_DIR / sport / f"{season}.json"
            persist_records((g.to_dict() for g in games), dest)
            all_games.extend(games)
            time.sleep(1)  # be polite to API limits
        except Exception as exc:
            LOGGER.error(
                "Failed to fetch season",
                extra={"sport": sport, "season": season, "error": str(exc)},
            )

    return all_games


def backfill_soccer_history(
    seasons: Iterable[str],
    leagues: Iterable[str] | None = None,
) -> list[GameRecord]:
    """Fetch and persist soccer fixtures across multiple leagues."""

    leagues = list(leagues or SOCCER_LEAGUES)
    if not leagues:
        LOGGER.warning("No soccer leagues configured; skipping backfill")
        return []

    games: list[GameRecord] = []
    for season in seasons:
        for league in leagues:
            path = SOCCER_HISTORY_LOCAL / f"{season}_{league}.json"
            if not path.exists():
                LOGGER.warning("Missing local soccer history file", extra={"path": str(path)})
                continue
            for payload in load_records(path):
                try:
                    games.append(GameRecord(**payload))
                except TypeError:
                    LOGGER.warning(
                        "Malformed soccer history row skipped", extra={"path": str(path)}
                    )
    if games:
        LOGGER.info("Loaded %s soccer matches from local history cache", len(games))
    return games


def backfill_odds_history(
    sport: str,
    seasons: Iterable[str],
    provider: str | None = None,
) -> list[OddsRecord]:
    sport_key = sport.lower()
    if sport_key == "soccer":
        odds = load_local_soccer_odds()
        if odds:
            LOGGER.info("Loaded %s soccer odds records from local cache", len(odds))
        else:
            LOGGER.warning(
                "Local soccer odds cache empty; run analytics.soccer_ingest.ingest_daily_odds"
            )
        return odds

    if sport_key == "nba":
        odds = load_local_nba_odds()
        if odds:
            LOGGER.info("Loaded %s NBA odds records from local cache", len(odds))
        else:
            LOGGER.warning("Local NBA odds cache empty; run analytics.nba_ingest.ingest_daily_odds")
        return odds

    provider = (provider or SPORTS_ODDS_PROVIDER).lower()
    if not SPORTS_ODDS_API_KEY:
        LOGGER.warning("SPORTS_ODDS_API_KEY missing; odds history backfill skipped")
        return []

    client = OddsProviderClient(provider=provider, api_key=SPORTS_ODDS_API_KEY)
    all_odds: list[OddsRecord] = []

    for season in seasons:
        # Some providers do not expose deep historical API endpoints.
        # We simulate backfill by taking periodic snapshots for current season and
        # expecting offline ingestion jobs to populate archived files.
        try:
            snapshot = client.fetch_odds_snapshot(sport)
            if snapshot:
                dest = ODDS_DIR / sport / f"{season}_{provider}.json"
                existing = load_records(dest)
                merged = existing + [record.to_dict() for record in snapshot]
                persist_records(merged, dest)
                all_odds.extend(snapshot)
            time.sleep(1)
        except Exception as exc:
            LOGGER.error(
                "Failed to fetch odds snapshot",
                extra={"sport": sport, "season": season, "error": str(exc)},
            )

    return all_odds


def generate_season_list(years: int) -> list[str]:
    """Return the list of seasons (strings) covering the last `years` seasons."""

    current_year = datetime.now(UTC).year
    return [str(year) for year in range(current_year, current_year - years, -1)]


__all__ = [
    "GameRecord",
    "OddsRecord",
    "SportradarClient",
    "APIFootballClient",
    "OddsProviderClient",
    "backfill_sportradar_history",
    "backfill_soccer_history",
    "backfill_odds_history",
    "generate_season_list",
    "load_records",
    "persist_records",
    "load_local_soccer_history",
    "load_local_soccer_odds",
    "load_local_nba_history",
    "load_local_nba_odds",
    "fetch_fixture_score",
]


def _load_json_records(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not directory.exists():
        return records
    for path in directory.glob("*.json"):
        for payload in load_records(path):
            records.append(payload)
    return records


def load_local_soccer_history() -> list[GameRecord]:
    records: list[GameRecord] = []
    for payload in _load_json_records(SOCCER_HISTORY_LOCAL):
        try:
            records.append(GameRecord(**payload))
        except TypeError:
            LOGGER.warning("Malformed soccer history row skipped", extra={"payload": payload})
    return records


def load_local_soccer_odds() -> list[OddsRecord]:
    odds: list[OddsRecord] = []
    for payload in _load_json_records(SOCCER_ODDS_LOCAL):
        try:
            odds.append(OddsRecord(**payload))
        except TypeError:
            LOGGER.warning("Malformed soccer odds row skipped", extra={"payload": payload})
    return odds


def load_local_nba_history() -> list[GameRecord]:
    records: list[GameRecord] = []
    for payload in _load_json_records(NBA_HISTORY_LOCAL):
        try:
            records.append(GameRecord(**payload))
        except TypeError:
            LOGGER.warning("Malformed NBA history row skipped", extra={"payload": payload})
    return records


def load_local_nba_odds() -> list[OddsRecord]:
    odds: list[OddsRecord] = []
    for payload in _load_json_records(NBA_ODDS_LOCAL):
        try:
            odds.append(OddsRecord(**payload))
        except TypeError:
            LOGGER.warning("Malformed NBA odds row skipped", extra={"payload": payload})
    return odds


def fetch_fixture_score(fixture_id: str) -> dict[str, Any] | None:
    if not RAPIDAPI_KEY:
        LOGGER.debug(
            "RAPIDAPI_KEY missing; skipping fixture score fetch", extra={"fixture_id": fixture_id}
        )
        return None
    try:
        client = RapidAPIScoresClient(RAPIDAPI_KEY)
    except (ValueError, ImportError) as exc:
        LOGGER.warning("RapidAPI scores client unavailable", extra={"error": str(exc)})
        return None

    payload = client.fetch_scores(fixture_id)
    if payload:
        snapshot_dir = SCORES_DIR / "rapidapi"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = snapshot_dir / f"{fixture_id}_{timestamp}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        LOGGER.info(
            "Saved RapidAPI score snapshot", extra={"fixture_id": fixture_id, "path": str(path)}
        )
    return payload
