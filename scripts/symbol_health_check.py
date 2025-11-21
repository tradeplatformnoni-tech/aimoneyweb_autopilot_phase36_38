#!/usr/bin/env python3
"""
Symbol Health Check
===================
Polls every configured SmartTrader symbol using the QuoteService pipeline so we
can detect stale / failing data providers before the trading loop hits them.

Outputs:
    - logs/symbol_health.log (human readable summary)
    - state/symbol_health.json (machine-readable snapshot)

Usage:
    python scripts/symbol_health_check.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trader.quote_service import get_quote_service  # type: ignore
from trader.smart_trader import load_allocations  # type: ignore

STATE_DIR = ROOT / "state"
LOG_DIR = ROOT / "logs"
STATE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

STATE_FILE = STATE_DIR / "symbol_health.json"
LOG_FILE = LOG_DIR / "symbol_health.log"


def log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(entry + "\n")


def main(max_age: int = 0, failure_threshold: int = 3) -> None:
    allocations = load_allocations()
    service = get_quote_service()
    results: dict[str, dict[str, Any]] = {}
    stats = defaultdict(int)

    log(f"🚦 Running symbol health check for {len(allocations)} symbols...")

    for symbol in sorted(allocations.keys()):
        start = time.time()
        entry: dict[str, Any] = {
            "weight": float(allocations[symbol]),
            "status": "unknown",
            "last_price": None,
            "source": None,
            "latency_ms": None,
        }
        try:
            quote = service.get_quote(symbol, max_age=max_age)
            if quote is None:
                entry["status"] = "failed"
                stats["failed"] += 1
            else:
                entry["status"] = "ok"
                entry["last_price"] = float(quote.last_price)
                entry["source"] = quote.source
                stats["ok"] += 1
        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
            stats["error"] += 1
        finally:
            entry["latency_ms"] = round((time.time() - start) * 1000, 2)
            results[symbol] = entry

    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": {
            "total": len(allocations),
            "ok": stats["ok"],
            "failed": stats["failed"],
            "error": stats["error"],
            "prune_candidates": [],
        },
        "symbols": results,
    }

    prune_candidates = [sym for sym, info in results.items() if info["status"] == "failed"]
    snapshot["summary"]["prune_candidates"] = prune_candidates
    STATE_FILE.write_text(json.dumps(snapshot, indent=2))

    log(
        f"✅ Symbol health snapshot saved • total={snapshot['summary']['total']} "
        f"ok={snapshot['summary']['ok']} failed={snapshot['summary']['failed']} "
        f"errors={snapshot['summary']['error']}"
    )


if __name__ == "__main__":
    max_age_env = os.getenv("SYMBOL_HEALTH_MAX_AGE", "0")
    try:
        max_age = int(max_age_env)
    except ValueError:
        max_age = 0
    main(max_age=max_age)
