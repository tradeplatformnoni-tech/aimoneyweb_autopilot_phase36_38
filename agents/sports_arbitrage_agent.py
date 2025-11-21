#!/usr/bin/env python3
"""Sports arbitrage scanner - find guaranteed profit opportunities across bookmakers.

This agent uses the Sportsbook API to identify arbitrage opportunities where the
combined implied probabilities from different bookmakers are less than 100%, creating
a risk-free profit opportunity. Sends Telegram alerts for instant action.
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

for directory in (STATE, LOGS):
    directory.mkdir(parents=True, exist_ok=True)

ARBITRAGE_FILE = STATE / "sports_arbitrage_opportunities.json"
ARBITRAGE_LOG = LOGS / "sports_arbitrage.log"

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARBITRAGE_ENABLED = os.getenv("SPORTS_ARBITRAGE_ENABLED", "true").lower() == "true"
MIN_PROFIT_PCT = float(os.getenv("SPORTS_ARBITRAGE_MIN_PROFIT", "0.015"))  # 1.5%
BANKROLL = float(os.getenv("SPORTS_BANKROLL_INITIAL", "1000"))
POLL_INTERVAL = int(os.getenv("SPORTS_ARBITRAGE_INTERVAL", "300"))  # 5 minutes


def send_telegram(message: str) -> None:
    """Send Telegram notification."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print("[arbitrage] Telegram credentials missing; skipping alert", flush=True)
        return
    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[arbitrage] Telegram send failed: {response.text}", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"[arbitrage] Telegram error: {exc}", flush=True)


def fetch_arbitrage_opportunities() -> list[dict[str, Any]]:
    """Fetch arbitrage opportunities from Sportsbook API."""
    if not RAPIDAPI_KEY:
        print("[arbitrage] RAPIDAPI_KEY not set", flush=True)
        return []

    try:
        import requests

        url = "https://sportsbook-api2.p.rapidapi.com/v0/advantages/"
        params = {"type": "ARBITRAGE"}
        headers = {
            "x-rapidapi-host": "sportsbook-api2.p.rapidapi.com",
            "x-rapidapi-key": RAPIDAPI_KEY,
        }

        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code != 200:
            print(
                f"[arbitrage] API error: {response.status_code} {response.text[:200]}", flush=True
            )
            return []

        data = response.json()
        opportunities = data.get("data", []) if isinstance(data, dict) else []
        return opportunities

    except Exception as exc:  # pragma: no cover
        print(f"[arbitrage] Error fetching arbitrage: {exc}", flush=True)
        return []


def calculate_arbitrage_stakes(
    odds_list: list[float], total_stake: float
) -> list[dict[str, float]]:
    """
    Calculate optimal stakes for arbitrage bet.

    Args:
        odds_list: List of decimal odds for each outcome
        total_stake: Total amount to wager across all outcomes

    Returns:
        List of dicts with {stake, profit} for each outcome
    """
    # Convert to implied probabilities
    implied_probs = [1.0 / odds for odds in odds_list]
    total_prob = sum(implied_probs)

    if total_prob >= 1.0:
        # Not an arbitrage opportunity
        return []

    # Guaranteed profit percentage
    profit_pct = (1.0 - total_prob) / total_prob

    # Calculate stakes proportional to implied probabilities
    stakes = []
    for i, prob in enumerate(implied_probs):
        stake = total_stake * prob / total_prob
        payout = stake * odds_list[i]
        profit = payout - total_stake
        stakes.append(
            {"stake": round(stake, 2), "payout": round(payout, 2), "profit": round(profit, 2)}
        )

    return stakes


def format_arbitrage_alert(opp: dict[str, Any], stakes: list[dict[str, float]]) -> str:
    """Format arbitrage opportunity as Telegram message."""
    sport = opp.get("sport", "Unknown")
    event = opp.get("event", "Unknown event")
    profit_pct = opp.get("profit_percentage", 0.0)
    timestamp = opp.get("timestamp", "")

    message = "🎯 *ARBITRAGE ALERT* 🎯\n\n"
    message += f"Sport: *{sport}*\n"
    message += f"Event: {event}\n"
    message += f"Profit: *{profit_pct:.2%}*\n"
    message += f"Time: {timestamp}\n\n"

    outcomes = opp.get("outcomes", [])
    for i, outcome in enumerate(outcomes):
        if i < len(stakes):
            book = outcome.get("bookmaker", "Unknown")
            side = outcome.get("outcome", "Unknown")
            odds = outcome.get("odds", 0.0)
            stake = stakes[i]["stake"]
            message += f"📌 {side} @ {book}\n"
            message += f"   Odds: {odds:.2f} | Stake: ${stake:.2f}\n"

    total_stake = sum(s["stake"] for s in stakes)
    total_profit = stakes[0]["profit"] if stakes else 0.0
    message += f"\n💰 Total Stake: ${total_stake:.2f}\n"
    message += f"✅ Guaranteed Profit: ${total_profit:.2f}\n"
    message += "\n⚡ Act fast - arbitrage windows close quickly!"

    return message


def process_arbitrage() -> None:
    """Main arbitrage scanning loop."""
    if not ARBITRAGE_ENABLED:
        print("[arbitrage] Arbitrage scanner disabled", flush=True)
        return

    print(
        f"[arbitrage] Scanning for arbitrage opportunities (min profit: {MIN_PROFIT_PCT:.2%})...",
        flush=True,
    )

    opportunities = fetch_arbitrage_opportunities()
    filtered_opps = []

    for opp in opportunities:
        profit_pct = opp.get("profit_percentage", 0.0)
        if profit_pct < MIN_PROFIT_PCT:
            continue

        # Extract odds for stake calculation
        outcomes = opp.get("outcomes", [])
        odds_list = [outcome.get("odds", 0.0) for outcome in outcomes]

        if not odds_list or any(o <= 1.0 for o in odds_list):
            continue

        # Calculate optimal stakes
        stakes = calculate_arbitrage_stakes(odds_list, BANKROLL * 0.05)  # Use 5% of bankroll
        if not stakes:
            continue

        # Store opportunity
        opp["calculated_stakes"] = stakes
        opp["discovered_at"] = datetime.now(UTC).isoformat()
        filtered_opps.append(opp)

        # Send alert
        message = format_arbitrage_alert(opp, stakes)
        send_telegram(message)
        print(f"[arbitrage] Found opportunity: {profit_pct:.2%} profit", flush=True)

    # Save opportunities
    if filtered_opps:
        ARBITRAGE_FILE.write_text(json.dumps(filtered_opps, indent=2))
        with ARBITRAGE_LOG.open("a", encoding="utf-8") as log:
            for opp in filtered_opps:
                log.write(json.dumps(opp) + "\n")

    print(f"[arbitrage] Scan complete - found {len(filtered_opps)} opportunities", flush=True)


def main() -> None:
    """Run arbitrage scanner continuously."""
    print("[arbitrage] Sports Arbitrage Scanner started", flush=True)
    print(f"[arbitrage] Min profit threshold: {MIN_PROFIT_PCT:.2%}", flush=True)
    print(f"[arbitrage] Poll interval: {POLL_INTERVAL}s", flush=True)

    while True:
        try:
            process_arbitrage()
        except KeyboardInterrupt:
            print("[arbitrage] Shutting down...", flush=True)
            break
        except Exception as exc:  # pragma: no cover
            print(f"[arbitrage] Error in main loop: {exc}", flush=True)
            import traceback

            traceback.print_exc()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
