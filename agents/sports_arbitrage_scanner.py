#!/usr/bin/env python3
"""Sports arbitrage scanner using local odds snapshots.

Scans local SofaScore odds snapshots to identify arbitrage opportunities across bookmakers.
Sends Telegram alerts when profitable arbitrage is detected (combined implied probability < 100%).
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
ODDS_SNAPSHOTS = ROOT / "data" / "odds_snapshots"

for directory in (STATE, LOGS):
    directory.mkdir(parents=True, exist_ok=True)

ARBITRAGE_FILE = STATE / "sports_arbitrage_opportunities.json"
ARBITRAGE_LOG = LOGS / "sports_arbitrage_scanner.log"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARBITRAGE_ENABLED = os.getenv("SPORTS_ARBITRAGE_ENABLED", "true").lower() == "true"
MIN_PROFIT_PCT = float(os.getenv("SPORTS_ARBITRAGE_MIN_PROFIT", "0.015"))  # 1.5%
BANKROLL = float(os.getenv("SPORTS_BANKROLL_INITIAL", "1000"))
POLL_INTERVAL = int(os.getenv("SPORTS_ARBITRAGE_INTERVAL", "1800"))  # 30 minutes


def log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    with ARBITRAGE_LOG.open("a") as f:
        f.write(line + "\n")


def send_telegram(message: str) -> None:
    """Send Telegram notification."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        log("[telegram] Credentials missing; skipping alert")
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            log(f"[telegram] Send failed: {response.text}")
    except Exception as exc:
        log(f"[telegram] Error: {exc}")


def load_latest_odds(sport: str) -> list[dict[str, Any]]:
    """Load the most recent odds snapshot for a sport."""
    snapshot_dir = ODDS_SNAPSHOTS / sport
    if not snapshot_dir.exists():
        return []

    latest_file = max(snapshot_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None)
    if not latest_file:
        return []

    try:
        with latest_file.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"[load_odds] Error reading {latest_file}: {exc}")
        return []


def find_arbitrage_in_odds(odds_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Scan odds records and identify arbitrage opportunities.

    Groups records by game_id and checks if different bookmakers create an arb.
    """
    opportunities: list[dict[str, Any]] = []

    # Group by game_id
    games: dict[str, list[dict[str, Any]]] = {}
    for record in odds_records:
        game_id = record.get("game_id")
        if not game_id:
            continue
        games.setdefault(game_id, []).append(record)

    for game_id, records in games.items():
        # Need moneyline/h2h market from at least one record
        home_odds_list: list[float] = []
        away_odds_list: list[float] = []
        providers: list[str] = []

        for rec in records:
            if rec.get("market") in ("h2h", "moneyline"):
                home_price = rec.get("home_price")
                away_price = rec.get("away_price")
                if home_price and away_price:
                    home_odds_list.append(float(home_price))
                    away_odds_list.append(float(away_price))
                    providers.append(rec.get("provider", "unknown"))

        if len(home_odds_list) < 2:
            continue  # Need multiple bookmakers

        # Find best odds for each side
        best_home = max(home_odds_list)
        best_away = max(away_odds_list)
        best_home_idx = home_odds_list.index(best_home)
        best_away_idx = away_odds_list.index(best_away)

        # Calculate combined implied probability
        implied_home = 1.0 / best_home
        implied_away = 1.0 / best_away
        total_prob = implied_home + implied_away

        if total_prob < 1.0:
            profit_pct = (1.0 - total_prob) / total_prob
            if profit_pct >= MIN_PROFIT_PCT:
                opportunities.append(
                    {
                        "game_id": game_id,
                        "sport": records[0].get("sport", "unknown"),
                        "home_odds": best_home,
                        "away_odds": best_away,
                        "home_provider": providers[best_home_idx],
                        "away_provider": providers[best_away_idx],
                        "profit_pct": round(profit_pct * 100, 2),
                        "total_implied_prob": round(total_prob * 100, 2),
                        "detected_at": datetime.now(UTC).isoformat(),
                    }
                )

    return opportunities


def calculate_stakes(home_odds: float, away_odds: float, total_stake: float) -> dict[str, float]:
    """Calculate optimal stakes for a two-outcome arbitrage."""
    implied_home = 1.0 / home_odds
    implied_away = 1.0 / away_odds
    total_prob = implied_home + implied_away

    if total_prob >= 1.0:
        return {}

    stake_home = total_stake * implied_home / total_prob
    stake_away = total_stake * implied_away / total_prob

    payout_home = stake_home * home_odds
    payout_away = stake_away * away_odds
    profit = min(payout_home, payout_away) - total_stake

    return {
        "stake_home": round(stake_home, 2),
        "stake_away": round(stake_away, 2),
        "payout_home": round(payout_home, 2),
        "payout_away": round(payout_away, 2),
        "profit": round(profit, 2),
    }


def format_alert(opp: dict[str, Any], stakes: dict[str, float]) -> str:
    """Format arbitrage opportunity as Telegram message."""
    return f"""🚨 **Arbitrage Opportunity Detected**

**Game**: {opp.get("game_id")}
**Sport**: {opp.get("sport")}
**Profit**: {opp.get("profit_pct")}%
**Total Implied Prob**: {opp.get("total_implied_prob")}%

**Home Side**:
  - Odds: {opp.get("home_odds")}
  - Provider: {opp.get("home_provider")}
  - Stake: ${stakes.get("stake_home", 0)}

**Away Side**:
  - Odds: {opp.get("away_odds")}
  - Provider: {opp.get("away_provider")}
  - Stake: ${stakes.get("stake_away", 0)}

**Guaranteed Profit**: ${stakes.get("profit", 0)}
"""


def scan_arbitrage() -> None:
    """Main arbitrage scanning loop."""
    if not ARBITRAGE_ENABLED:
        log("[arbitrage] Disabled via SPORTS_ARBITRAGE_ENABLED")
        return

    log("[arbitrage] Starting scanner...")

    while True:
        try:
            all_opportunities: list[dict[str, Any]] = []

            for sport in ("nba", "soccer"):
                odds_records = load_latest_odds(sport)
                if not odds_records:
                    log(f"[{sport}] No odds snapshots found")
                    continue

                opportunities = find_arbitrage_in_odds(odds_records)
                log(f"[{sport}] Found {len(opportunities)} arbitrage opportunities")

                for opp in opportunities:
                    stakes = calculate_stakes(
                        opp["home_odds"],
                        opp["away_odds"],
                        BANKROLL * 0.1,  # Risk 10% of bankroll per arb
                    )
                    if stakes:
                        opp["stakes"] = stakes
                        all_opportunities.append(opp)
                        alert = format_alert(opp, stakes)
                        send_telegram(alert)

            # Persist opportunities
            if all_opportunities:
                payload = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "opportunities": all_opportunities,
                    "count": len(all_opportunities),
                }
                ARBITRAGE_FILE.write_text(json.dumps(payload, indent=2))
                log(f"[arbitrage] Saved {len(all_opportunities)} opportunities to {ARBITRAGE_FILE}")

        except Exception as exc:
            log(f"[arbitrage] Scan error: {exc}")

        log(f"[arbitrage] Sleeping {POLL_INTERVAL}s before next scan")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    scan_arbitrage()
