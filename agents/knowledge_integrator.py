#!/usr/bin/env python3
"""
Knowledge Integrator - Enhanced for Phase 1300-1500
Fetches headlines/signals from Twitter/Reddit/GitHub
Connects data feeds to revenue agents (dropshipping, collectibles, luxury, content)
"""

import json
import os
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
OUT = STATE / "knowledge_snap.json"

# Revenue agent data feeds
TRENDING_PRODUCTS = STATE / "trending_products.json"
EVENT_SCHEDULE = STATE / "event_schedule.json"
SPORTS_ODDS = STATE / "sports_odds.json"


def fetch_twitter_trends() -> list[str]:
    """Fetch trending topics/products from Twitter (if API key available)."""
    token = os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        return []

    # TODO: Implement actual Twitter API v2 calls
    # For now, return placeholder
    return ["(stub) trending product: fitness gadget", "(stub) trending: luxury watch"]


def fetch_reddit_trends() -> list[str]:
    """Fetch trending topics from Reddit (if API keys available)."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    secret = os.getenv("REDDIT_SECRET")
    if not (client_id and secret):
        return []

    # TODO: Implement Reddit API calls
    return ["(stub) r/investing: hot stock discussion"]


def fetch_github_signals() -> list[str]:
    """Fetch GitHub repo signals (if token available)."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return []

    # TODO: Implement GitHub API for trending repos/languages
    return ["(stub) trending repo: AI trading framework"]


def extract_product_signals(sources: dict[str, Any]) -> list[dict[str, str]]:
    """Extract product/trend signals from knowledge sources for dropshipping agent."""
    products = []

    for source_name, items in sources.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and any(
                    kw in item.lower() for kw in ["product", "gadget", "trend", "item"]
                ):
                    products.append(
                        {"source": source_name, "signal": item, "timestamp": time.time()}
                    )

    return products[:10]  # Top 10


def extract_event_signals(sources: dict[str, Any]) -> list[dict[str, str]]:
    """Extract event signals for ticket arbitrage agent."""
    events = []

    for source_name, items in sources.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str) and any(
                    kw in item.lower() for kw in ["concert", "game", "event", "show", "ticket"]
                ):
                    events.append({"source": source_name, "signal": item, "timestamp": time.time()})

    return events[:10]


def main():
    """Main knowledge integration loop."""
    payload: dict[str, Any] = {"ts": time.time(), "sources": {}}

    # Twitter/X
    if os.getenv("TWITTER_BEARER_TOKEN"):
        payload["sources"]["twitter"] = fetch_twitter_trends()
    else:
        payload["sources"]["twitter"] = "no key"

    # Reddit
    if os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_SECRET"):
        payload["sources"]["reddit"] = fetch_reddit_trends()
    else:
        payload["sources"]["reddit"] = "no key"

    # GitHub
    if os.getenv("GITHUB_TOKEN"):
        payload["sources"]["github"] = fetch_github_signals()
    else:
        payload["sources"]["github"] = "no key"

    # Extract signals for revenue agents
    payload["trending_products"] = extract_product_signals(payload["sources"])
    payload["event_signals"] = extract_event_signals(payload["sources"])

    # Save main knowledge snapshot
    OUT.write_text(json.dumps(payload, indent=2))

    # Save revenue agent feeds
    if payload["trending_products"]:
        TRENDING_PRODUCTS.write_text(json.dumps(payload["trending_products"], indent=2))

    if payload["event_signals"]:
        EVENT_SCHEDULE.write_text(json.dumps(payload["event_signals"], indent=2))

    print(
        f"🔎 Knowledge Integrator refreshed → {OUT} ({len(payload['trending_products'])} products, {len(payload['event_signals'])} events)",
        flush=True,
    )


if __name__ == "__main__":
    while True:
        try:
            main()
            time.sleep(3600)  # Update every hour
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[knowledge_integrator] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(300)
