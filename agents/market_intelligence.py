#!/usr/bin/env python3
"""
Market Intelligence Agent - World-Class Multi-Source Research
Aggregates data from Reddit, Twitter, Financial News, Fed, Telegram, and more
Feeds signals to trading agent for informed decisions
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None
    print("[market_intelligence] Install requests: pip install requests")

# Detect Render environment - use Render paths if in cloud
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"

if RENDER_MODE:
    ROOT = Path("/opt/render/project/src")
else:
    ROOT = Path(os.path.expanduser("~/neolight"))

STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

INTELLIGENCE_FILE = STATE / "market_intelligence.json"

# API Keys (env-driven)
TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_SECRET = os.getenv("REDDIT_SECRET", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")  # Federal Reserve Economic Data


def fetch_reddit_sentiment(symbol: str) -> dict[str, Any] | None:
    """Fetch Reddit sentiment for symbol (r/wallstreetbets, r/investing, r/stocks)."""
    if not (REDDIT_CLIENT_ID and REDDIT_SECRET):
        return None

    if not requests:
        return None

    try:
        # Reddit API OAuth
        auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_SECRET)
        data = {"grant_type": "client_credentials"}
        headers = {"User-Agent": "NeoLight/1.0"}
        res = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=10,
        )
        token = res.json().get("access_token")

        if not token:
            return None

        # Search Reddit for symbol mentions
        headers = {"Authorization": f"bearer {token}", "User-Agent": "NeoLight/1.0"}
        subreddits = ["wallstreetbets", "investing", "stocks", "StockMarket", "cryptocurrency"]
        mentions = 0
        upvotes = 0

        for sub in subreddits[:2]:  # Limit to avoid rate limits
            try:
                url = f"https://oauth.reddit.com/r/{sub}/search.json?q={symbol}&limit=5"
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    for post in data.get("data", {}).get("children", [])[:5]:
                        mentions += 1
                        upvotes += post.get("data", {}).get("ups", 0)
            except:
                continue

        if mentions > 0:
            return {
                "mentions": mentions,
                "avg_upvotes": upvotes / mentions if mentions > 0 else 0,
                "sentiment_score": min(1.0, upvotes / (mentions * 10)),  # Normalized
            }
    except Exception:
        pass

    return None


def fetch_twitter_sentiment(symbol: str) -> dict[str, Any] | None:
    """Fetch Twitter/X sentiment using Twitter API v2."""
    if not TWITTER_BEARER:
        return None

    if not requests:
        return None

    try:
        # Twitter API v2 search
        headers = {"Authorization": f"Bearer {TWITTER_BEARER}"}
        url = f"https://api.twitter.com/2/tweets/search/recent?query={symbol}&max_results=10"
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code == 200:
            data = res.json()
            tweets = data.get("data", [])

            # Simple sentiment: count positive keywords
            positive_keywords = ["buy", "bull", "moon", "pump", "gains", "profit"]
            negative_keywords = ["sell", "bear", "crash", "dump", "loss", "drop"]

            positive = sum(
                1
                for t in tweets
                if any(kw in t.get("text", "").lower() for kw in positive_keywords)
            )
            negative = sum(
                1
                for t in tweets
                if any(kw in t.get("text", "").lower() for kw in negative_keywords)
            )

            if len(tweets) > 0:
                sentiment = (positive - negative) / len(tweets)
                return {
                    "tweets": len(tweets),
                    "sentiment_score": sentiment,
                    "positive": positive,
                    "negative": negative,
                }
    except Exception:
        pass

    return None


def fetch_news_sentiment(symbol: str) -> dict[str, Any] | None:
    """Fetch financial news sentiment."""
    if not NEWS_API_KEY:
        return None

    if not requests:
        return None

    try:
        url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={NEWS_API_KEY}&sortBy=publishedAt&pageSize=10"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            articles = data.get("articles", [])

            # Simple sentiment analysis
            positive_keywords = ["up", "surge", "gain", "rise", "bull", "growth"]
            negative_keywords = ["down", "fall", "drop", "bear", "decline", "loss"]

            sentiments = []
            for article in articles[:5]:
                title = article.get("title", "").lower()
                pos = sum(1 for kw in positive_keywords if kw in title)
                neg = sum(1 for kw in negative_keywords if kw in title)
                sentiments.append(1.0 if pos > neg else (-1.0 if neg > pos else 0.0))

            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                return {
                    "articles": len(articles),
                    "sentiment_score": avg_sentiment,
                    "latest_headlines": [a.get("title") for a in articles[:3]],
                }
    except Exception:
        pass

    return None


def fetch_fed_data() -> dict[str, Any] | None:
    """Fetch Federal Reserve economic data (interest rates, inflation, etc.)."""
    if not FRED_API_KEY:
        return None

    if not requests:
        return None

    try:
        # Get latest Fed Funds Rate
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key={FRED_API_KEY}&file_type=json&limit=1&sort_order=desc"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            observations = data.get("observations", [])
            if observations:
                latest = observations[0]
                rate = float(latest.get("value", 0))
                return {
                    "fed_funds_rate": rate,
                    "date": latest.get("date"),
                    "impact": "bearish" if rate > 5.0 else "bullish",  # Simplified
                }
    except Exception:
        pass

    return None


def fetch_telegram_signals() -> dict[str, Any] | None:
    """Fetch signals from Telegram trading channels (if configured)."""
    # This would require Telegram Bot API integration
    # Placeholder for now
    return None


def aggregate_intelligence(symbols: list[str]) -> dict[str, Any]:
    """Aggregate all intelligence sources for given symbols."""
    intelligence = {
        "timestamp": datetime.now(UTC).isoformat(),
        "sources": {},
        "signals": {},
        "fed_data": None,
    }

    # Fetch Fed data (once, applies to all symbols)
    intelligence["fed_data"] = fetch_fed_data()

    # For each symbol, aggregate sources
    for symbol in symbols:
        signals = {
            "reddit": fetch_reddit_sentiment(symbol),
            "twitter": fetch_twitter_sentiment(symbol),
            "news": fetch_news_sentiment(symbol),
            "telegram": fetch_telegram_signals(),
        }

        # Calculate composite sentiment
        sentiments = [
            s.get("sentiment_score") for s in signals.values() if s and "sentiment_score" in s
        ]
        if sentiments:
            composite = sum(sentiments) / len(sentiments)
            signals["composite_sentiment"] = composite
            signals["recommendation"] = (
                "BUY" if composite > 0.3 else ("SELL" if composite < -0.3 else "HOLD")
            )

        intelligence["signals"][symbol] = signals

    return intelligence


def main():
    """Main intelligence gathering loop."""
    print(
        f"[market_intelligence] Starting market intelligence @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    # Get symbols from allocations
    alloc_file = RUNTIME / "allocations_override.json"
    symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]  # Default
    if alloc_file.exists():
        try:
            data = json.loads(alloc_file.read_text())
            symbols = list(data.get("allocations", {}).keys())
        except:
            pass

    while True:
        try:
            # Aggregate intelligence
            intelligence = aggregate_intelligence(symbols)

            # Save to file
            INTELLIGENCE_FILE.write_text(json.dumps(intelligence, indent=2))

            print(
                f"[market_intelligence] Intelligence updated for {len(symbols)} symbols", flush=True
            )

            # Log summary
            for sym, signals in intelligence.get("signals", {}).items():
                composite = signals.get("composite_sentiment", 0)
                rec = signals.get("recommendation", "HOLD")
                print(f"  {sym}: {rec} (sentiment: {composite:.2f})", flush=True)

            # Update every 15 minutes
            time.sleep(900)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[market_intelligence] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(300)


if __name__ == "__main__":
    main()
