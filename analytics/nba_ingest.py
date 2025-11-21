from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from analytics.scrape_supervisor import ScraperTask, ScrapeSupervisor
from analytics.sofascore_client import (
    SofaScoreClient,
    extract_moneyline_prices,
    select_moneyline_market,
)
from analytics.sports_data_manager import GameRecord, OddsRecord

ROOT = Path("~/neolight").expanduser()
HISTORY_DIR = ROOT / "data" / "sports_history" / "nba"
ODDS_DIR = ROOT / "data" / "odds_snapshots" / "nba"
INJURY_FILE = ROOT / "data" / "sports_injuries" / "nba_injuries.json"

for directory in (HISTORY_DIR, ODDS_DIR, INJURY_FILE.parent):
    directory.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("nba_ingest")
if not LOGGER.handlers:
    handler = logging.FileHandler(ROOT / "logs" / "data_ingestion.log")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s | %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


def fetch_bballref_season(season: str) -> pd.DataFrame:
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    tables = pd.read_html(url)
    if not tables:
        raise ValueError(f"No tables found at {url}")
    df = tables[0]
    df = df.dropna(how="all")
    df = df[df["Date"] != "Date"]
    df = df[df["Visitor/Neutral"] != "Visitor/Neutral"]
    return df


def normalise_bballref(df: pd.DataFrame, season: str) -> list[GameRecord]:
    records: list[GameRecord] = []
    for _, row in df.iterrows():
        date_str = str(row.get("Date", "")).strip()
        if not date_str:
            continue
        try:
            scheduled = datetime.strptime(date_str, "%a, %b %d, %Y").date().isoformat()
        except ValueError:
            try:
                scheduled = datetime.strptime(date_str, "%b %d, %Y").date().isoformat()
            except ValueError:
                scheduled = date_str

        away_team = str(row.get("Visitor/Neutral", "")).strip()
        home_team = str(row.get("Home/Neutral", "")).strip()
        if not home_team or not away_team:
            continue

        def _safe_int(value: any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        away_pts = _safe_int(row.get("PTS"))
        home_pts = _safe_int(row.get("PTS.1"))
        status = "complete" if home_pts is not None and away_pts is not None else "scheduled"

        record = GameRecord(
            sport="nba",
            game_id=f"NBA_{season}_{scheduled}_{away_team}_at_{home_team}",
            season=season,
            scheduled=scheduled,
            home_team=home_team,
            away_team=away_team,
            home_score=home_pts,
            away_score=away_pts,
            status=status,
        )
        records.append(record)
    return records


NBA_TEAM_CANONICAL: dict[str, str] = {
    "atlanta hawks": "Atlanta Hawks",
    "boston celtics": "Boston Celtics",
    "brooklyn nets": "Brooklyn Nets",
    "charlotte hornets": "Charlotte Hornets",
    "chicago bulls": "Chicago Bulls",
    "cleveland cavaliers": "Cleveland Cavaliers",
    "dallas mavericks": "Dallas Mavericks",
    "denver nuggets": "Denver Nuggets",
    "detroit pistons": "Detroit Pistons",
    "golden state warriors": "Golden State Warriors",
    "houston rockets": "Houston Rockets",
    "indiana pacers": "Indiana Pacers",
    "la clippers": "Los Angeles Clippers",
    "los angeles clippers": "Los Angeles Clippers",
    "los angeles lakers": "Los Angeles Lakers",
    "la lakers": "Los Angeles Lakers",
    "memphis grizzlies": "Memphis Grizzlies",
    "miami heat": "Miami Heat",
    "milwaukee bucks": "Milwaukee Bucks",
    "minnesota timberwolves": "Minnesota Timberwolves",
    "new orleans pelicans": "New Orleans Pelicans",
    "new york knicks": "New York Knicks",
    "oklahoma city thunder": "Oklahoma City Thunder",
    "orlando magic": "Orlando Magic",
    "philadelphia 76ers": "Philadelphia 76ers",
    "phoenix suns": "Phoenix Suns",
    "portland trail blazers": "Portland Trail Blazers",
    "sacramento kings": "Sacramento Kings",
    "san antonio spurs": "San Antonio Spurs",
    "toronto raptors": "Toronto Raptors",
    "utah jazz": "Utah Jazz",
    "washington wizards": "Washington Wizards",
}


def normalize_team_name(name: str) -> str:
    key = (name or "").strip().lower()
    return NBA_TEAM_CANONICAL.get(key, name.strip())


def build_sofascore_odds(
    events: Iterable[dict[str, Any]],
    client: SofaScoreClient,
) -> list[OddsRecord]:
    odds_records: list[OddsRecord] = []
    for event in events:
        tournament = event.get("tournament") or {}
        unique = event.get("uniqueTournament") or tournament.get("uniqueTournament") or tournament
        slug = (unique.get("slug") or tournament.get("slug") or "").lower()
        if "nba" not in slug:
            continue
        event_id = event.get("id")
        if not event_id:
            continue
        home_team_raw = (event.get("homeTeam") or {}).get("name") or ""
        away_team_raw = (event.get("awayTeam") or {}).get("name") or ""
        home_team = normalize_team_name(home_team_raw)
        away_team = normalize_team_name(away_team_raw)
        if not home_team or not away_team:
            continue

        start_ts = event.get("startTimestamp") or event.get("startTime")
        if not start_ts:
            continue
        try:
            scheduled_date = datetime.utcfromtimestamp(int(start_ts)).date()
        except Exception:
            continue

        season_year = scheduled_date.year + 1 if scheduled_date.month >= 7 else scheduled_date.year
        game_id = f"NBA_{season_year}_{scheduled_date.isoformat()}_{away_team}_at_{home_team}"

        odds_payload = client.fetch_event_odds(event_id)
        if not odds_payload:
            continue
        market = select_moneyline_market(odds_payload.get("markets") or [])
        prices = extract_moneyline_prices(market, home_team, away_team)
        if not prices["home"] and not prices["away"]:
            continue
        odds_records.append(
            OddsRecord(
                sport="nba",
                game_id=game_id,
                provider="sofascore",
                collected_at=datetime.utcnow().isoformat(),
                home_price=prices["home"],
                away_price=prices["away"],
                draw_price=prices["draw"],
                market="moneyline",
            )
        )
    return odds_records


def persist_history(records: list[GameRecord], season: str) -> Path:
    path = HISTORY_DIR / f"{season}_NBA.json"
    path.write_text(json.dumps([record.to_dict() for record in records], indent=2))
    return path


def ingest_history(
    seasons: Sequence[str],
    supervisor: ScrapeSupervisor | None = None,
) -> None:
    supervisor = supervisor or ScrapeSupervisor()

    for season in seasons:

        def runner(season=season) -> dict[str, any]:
            df = fetch_bballref_season(season)
            records = normalise_bballref(df, season)
            persist_history(records, season)
            return {
                "season": season,
                "record_count": len(records),
                "target": str(HISTORY_DIR / f"{season}_NBA.json"),
            }

        task = ScraperTask(
            name=f"nba_history_{season}",
            runner=runner,
            validators=[
                lambda payload: None if payload["record_count"] else {"records": ["0 entries"]}
            ],
            max_retries=2,
        )
        supervisor.run_task(task)


def ingest_odds(days: int = 2) -> Path | None:
    client = SofaScoreClient("basketball")
    supervisor = ScrapeSupervisor()

    def runner() -> dict[str, Any]:
        events = client.fetch_events(days=days)
        cutoff = datetime.utcnow().timestamp() - 3600  # ignore games finished over an hour ago
        filtered: list[dict[str, Any]] = []
        for event in events:
            start_ts = event.get("startTimestamp") or event.get("startTime")
            try:
                start_value = float(start_ts)
            except (TypeError, ValueError):
                continue
            if start_value < cutoff:
                continue
            filtered.append(event)
            if len(filtered) >= 40:
                break

        odds = build_sofascore_odds(filtered, client)
        if not odds:
            return {"count": 0}
        destination = ODDS_DIR / f"odds_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
        destination.write_text(json.dumps([record.to_dict() for record in odds], indent=2))
        return {"count": len(odds), "target": str(destination)}

    outcome = supervisor.run_task(
        ScraperTask(
            name="nba_odds_sofascore",
            runner=runner,
            validators=[
                lambda payload: None if payload.get("count") else {"odds": ["empty snapshot"]}
            ],
            max_retries=2,
        )
    )
    if not outcome:
        LOGGER.warning("NBA odds scraping task returned no payload")
        return None
    if not outcome.get("count"):
        LOGGER.warning("SofaScore returned no NBA odds data")
        return None

    LOGGER.info("Saved %s NBA odds entries to %s", outcome["count"], outcome["target"])
    return Path(outcome["target"])


def compute_injury_impact(status: str) -> float:
    status_lower = status.lower()
    if "out" in status_lower or "injury reserve" in status_lower:
        return 1.0
    if "doubtful" in status_lower:
        return 0.7
    if "questionable" in status_lower or "day-to-day" in status_lower:
        return 0.4
    if "probable" in status_lower:
        return 0.2
    return 0.0


def ingest_injuries() -> Path | None:
    url = "https://www.espn.com/nba/injuries"
    tables = pd.read_html(url)
    if not tables:
        LOGGER.warning("Could not parse ESPN NBA injuries table")
        return None

    injuries: dict[str, float] = {}
    for table in tables:
        if table.empty:
            continue
        upper_columns = {str(col).upper(): col for col in table.columns}
        if "TEAM" not in upper_columns:
            continue
        team_col = upper_columns["TEAM"]
        status_col = upper_columns.get("STATUS") or upper_columns.get("INJURY")
        for _, row in table.iterrows():
            team = str(row.get(team_col) or "").strip()
            status = str(row.get(status_col, "")).strip() if status_col else ""
            if not team:
                continue
            injuries[team] = injuries.get(team, 0.0) + compute_injury_impact(status)

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "teams": [{"team": team, "impact": round(score, 3)} for team, score in injuries.items()],
    }
    INJURY_FILE.write_text(json.dumps(payload, indent=2))
    LOGGER.info("Saved injury snapshot to %s", INJURY_FILE)
    return INJURY_FILE


def run_full_ingestion(
    seasons: Sequence[str],
    ingest_odds_snapshot: bool = True,
    ingest_injury_snapshot: bool = True,
) -> None:
    LOGGER.info("Starting NBA ingestion pipeline")
    supervisor = ScrapeSupervisor()
    ingest_history(seasons, supervisor)
    if ingest_odds_snapshot:
        ingest_odds()
    if ingest_injury_snapshot:
        ingest_injuries()
    LOGGER.info("NBA ingestion complete")


__all__ = [
    "run_full_ingestion",
    "ingest_history",
    "ingest_odds",
    "ingest_injuries",
]
