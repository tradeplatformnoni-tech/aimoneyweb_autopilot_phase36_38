from __future__ import annotations

import csv
import json
import logging
import time
from collections.abc import Iterable, Sequence
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import requests

from analytics.scrape_supervisor import ScraperTask, ScrapeSupervisor
from analytics.sofascore_client import (
    SofaScoreClient,
    extract_moneyline_prices,
    select_moneyline_market,
)
from analytics.sports_data_manager import GameRecord, OddsRecord

LOGGER = logging.getLogger("soccer_ingest")
if not LOGGER.handlers:
    handler = logging.FileHandler(Path("~/neolight/logs/data_ingestion.log").expanduser())
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s | %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)

ROOT = Path("~/neolight").expanduser()
RAW_DIR = ROOT / "data" / "raw" / "soccer"
HISTORY_DIR = ROOT / "data" / "sports_history" / "soccer"
ODDS_DIR = ROOT / "data" / "odds_snapshots" / "soccer"

RAW_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
ODDS_DIR.mkdir(parents=True, exist_ok=True)


FBREF_DATASETS: dict[str, str] = {
    "EPL": "https://fbref.com/en/comps/9/{season}/schedule/{season}-Premier-League-Scores-and-Fixtures",
    "LaLiga": "https://fbref.com/en/comps/12/{season}/schedule/{season}-La-Liga-Scores-and-Fixtures",
    "SerieA": "https://fbref.com/en/comps/11/{season}/schedule/{season}-Serie-A-Scores-and-Fixtures",
}

FOOTBALL_DATA_CODES: dict[str, str] = {
    "EPL": "E0",
    "LaLiga": "SP1",
    "SerieA": "I1",
    "Bundesliga": "D1",
    "Ligue1": "F1",
}

SOFASCORE_LEAGUE_KEYWORDS: dict[str, list[str]] = {
    "EPL": ["premier-league"],
    "LaLiga": ["laliga", "la-liga"],
    "SerieA": ["serie-a"],
    "Bundesliga": ["bundesliga"],
    "Ligue1": ["ligue-1"],
    "Champions": ["uefa-champions-league"],
    "MLS": ["mls", "major-league-soccer"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
}


def fetch_fbref_schedule(url: str) -> list[dict[str, str]]:
    response = requests.get(url + ".csv", headers=HEADERS, timeout=30)
    response.raise_for_status()
    decoded = response.content.decode("utf-8")
    reader = csv.DictReader(StringIO(decoded))
    return list(reader)


def season_to_code(season: str) -> str:
    """Convert numeric season (e.g., 2024) to football-data code (2425)."""
    try:
        year = int(season)
    except ValueError:
        return season
    first = str(year % 100).zfill(2)
    second = str((year + 1) % 100).zfill(2)
    return f"{first}{second}"


def fetch_football_data_csv(league: str, season: str) -> list[dict[str, str]] | None:
    code = FOOTBALL_DATA_CODES.get(league)
    if not code:
        LOGGER.warning("League %s not mapped for football-data", league)
        return None
    season_code = season_to_code(season)
    url = f"https://www.football-data.co.uk/mmz4281/{season_code}/{code}.csv"
    response = requests.get(url, timeout=30)
    if response.status_code == 404:
        LOGGER.warning("Football-data dataset missing: %s", url)
        return None
    response.raise_for_status()
    reader = csv.DictReader(StringIO(response.content.decode("utf-8", errors="ignore")))
    return list(reader)


def normalize_fbref_row(row: dict[str, str], league: str, season: str) -> GameRecord | None:
    if not row.get("Date"):
        return None
    try:
        scheduled = datetime.strptime(row["Date"], "%Y-%m-%d").isoformat()
    except ValueError:
        scheduled = row["Date"]

    home = row.get("Home") or row.get("Home Team") or ""
    away = row.get("Away") or row.get("Away Team") or ""
    if not home or not away:
        return None

    def _safe_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return GameRecord(
        sport="soccer",
        game_id=f"{league}_{season}_{home}_{away}_{row.get('Date', '')}",
        season=season,
        scheduled=scheduled,
        home_team=home,
        away_team=away,
        home_score=_safe_int(row.get("Goals For") or row.get("GF")),
        away_score=_safe_int(row.get("Goals Against") or row.get("GA")),
        status="complete" if row.get("Goals For") else "scheduled",
    )


def persist_game_records(records: Iterable[GameRecord], league: str, season: str) -> Path:
    payload = [record.to_dict() for record in records]
    path = HISTORY_DIR / f"{season}_{league}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def ingest_seasons(
    seasons: Sequence[str],
    leagues: Sequence[str] | None = None,
    supervisor: ScrapeSupervisor | None = None,
) -> None:
    supervisor = supervisor or ScrapeSupervisor()
    leagues = list(leagues or FBREF_DATASETS.keys())

    for league in leagues:
        for season in seasons:

            def runner(league=league, season=season) -> dict[str, any]:
                rows = fetch_football_data_csv(league, season)
                if rows:
                    records = [
                        GameRecord(
                            sport="soccer",
                            game_id=f"{league}_{season}_{row.get('Date')}_{row.get('HomeTeam')}_{row.get('AwayTeam')}",
                            season=season,
                            scheduled=row.get("Date", ""),
                            home_team=row.get("HomeTeam", ""),
                            away_team=row.get("AwayTeam", ""),
                            home_score=int(row["FTHG"]) if row.get("FTHG") else None,
                            away_score=int(row["FTAG"]) if row.get("FTAG") else None,
                            status="complete" if row.get("FTHG") else "scheduled",
                        )
                        for row in rows
                        if row.get("HomeTeam") and row.get("AwayTeam")
                    ]
                    records = [
                        record for record in records if record.home_team and record.away_team
                    ]
                    persist_game_records(records, league, season)
                    return {
                        "league": league,
                        "season": season,
                        "record_count": len(records),
                        "source": "football-data.co.uk",
                    }

                template = FBREF_DATASETS.get(league)
                if not template:
                    raise ValueError(f"No dataset available for league {league}")
                url = template.format(season=season)
                fbref_records = fetch_fbref_schedule(url)
                game_records = [normalize_fbref_row(row, league, season) for row in fbref_records]
                game_records = [record for record in game_records if record]
                persist_game_records(game_records, league, season)
                return {
                    "league": league,
                    "season": season,
                    "record_count": len(game_records),
                    "source": "fbref.com",
                }

            task = ScraperTask(
                name=f"soccer_hist_{league}_{season}",
                runner=runner,
                validators=[
                    lambda payload: None if payload["record_count"] else {"records": ["0 entries"]}
                ],
                max_retries=2,
            )
            supervisor.run_task(task)


def _matches_league(event: dict[str, Any], league: str) -> bool:
    tournament = event.get("tournament") or {}
    slug = (tournament.get("slug") or "").lower()
    name = (tournament.get("name") or "").lower()
    category = (tournament.get("category") or {}).get("name", "").lower()
    keywords = SOFASCORE_LEAGUE_KEYWORDS.get(league, [league.lower()])
    for keyword in keywords:
        keyword = keyword.lower()
        if keyword in slug or keyword in name or keyword in category:
            return True
    return False


def build_odds_from_sofascore(
    client: SofaScoreClient,
    events: Iterable[dict[str, Any]],
    league: str,
    seen_ids: set[int],
) -> list[OddsRecord]:
    odds: list[OddsRecord] = []
    for event in events:
        if not _matches_league(event, league):
            continue
        event_id = event.get("id")
        if event_id is None:
            continue
        try:
            event_id_int = int(event_id)
        except (TypeError, ValueError):
            continue
        if event_id_int in seen_ids:
            continue

        home_team = (event.get("homeTeam") or {}).get("name") or ""
        away_team = (event.get("awayTeam") or {}).get("name") or ""
        if not home_team or not away_team:
            continue

        odds_payload = client.fetch_event_odds(event_id_int)
        time.sleep(0.25)
        if not odds_payload:
            continue

        market = select_moneyline_market(odds_payload.get("markets") or [])
        prices = extract_moneyline_prices(market, home_team, away_team)
        if not prices["home"] and not prices["away"] and not prices["draw"]:
            continue

        odds.append(
            OddsRecord(
                sport="soccer",
                game_id=f"{league}_{event_id_int}",
                provider="sofascore",
                collected_at=datetime.utcnow().isoformat(),
                home_price=prices["home"],
                away_price=prices["away"],
                draw_price=prices["draw"],
                market="moneyline",
            )
        )
        seen_ids.add(event_id_int)
    return odds


def ingest_daily_odds(
    leagues: Sequence[str] | None = None,
    days: int = 2,
) -> Path | None:
    leagues = list(leagues or SOFASCORE_LEAGUE_KEYWORDS.keys())
    client = SofaScoreClient("football")
    supervisor = ScrapeSupervisor()

    def runner() -> dict[str, Any]:
        events = client.fetch_events(days=days)
        seen_ids: set[int] = set()
        snapshots: list[OddsRecord] = []
        for league in leagues:
            league_odds = build_odds_from_sofascore(client, events, league, seen_ids)
            if league_odds:
                snapshots.extend(league_odds)
        if not snapshots:
            return {"count": 0}
        destination = ODDS_DIR / f"odds_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
        destination.write_text(json.dumps([record.to_dict() for record in snapshots], indent=2))
        return {"count": len(snapshots), "target": str(destination)}

    outcome = supervisor.run_task(
        ScraperTask(
            name="soccer_odds_sofascore",
            runner=runner,
            validators=[
                lambda payload: None if payload.get("count") else {"odds": ["empty snapshot"]}
            ],
            max_retries=2,
        )
    )
    if not outcome.get("count"):
        LOGGER.warning("SofaScore returned no soccer odds data")
        return None

    LOGGER.info("Saved %s soccer odds snapshots to %s", outcome["count"], outcome["target"])
    return Path(outcome["target"])


def run_full_ingestion(
    seasons: Sequence[str],
    leagues: Sequence[str] | None = None,
    ingest_odds: bool = True,
) -> None:
    LOGGER.info("Starting soccer ingestion pipeline")
    supervisor = ScrapeSupervisor()
    ingest_seasons(seasons, leagues, supervisor)

    if ingest_odds:
        ingest_daily_odds(leagues)

    LOGGER.info("Soccer ingestion complete")


__all__ = [
    "ingest_seasons",
    "ingest_daily_odds",
    "run_full_ingestion",
]
