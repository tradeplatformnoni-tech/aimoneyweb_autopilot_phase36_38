#!/usr/bin/env python3
"""
Weekly AI cohort rebalance and commodity tail-risk snapshot.

Creates a point-in-time summary for:
  - AI rotation basket (allocations, top constituents, weekly returns)
  - Macro/commodity hedge exposures (GLD, SLV, USO, TLT, IEF)

Outputs a JSON plan in state/weekly_ai_rebalance_plan.json for dashboards/guardian.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

LOGS.mkdir(parents=True, exist_ok=True)
STATE.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "weekly_ai_rebalance.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("weekly_ai_rebalance")

try:
    import yfinance as yf  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    yf = None
    logger.warning("yfinance not installed; price metrics will be omitted")


@dataclass
class SymbolSnapshot:
    symbol: str
    weight: float
    price: float | None
    weekly_return_pct: float | None


def load_allocations() -> tuple[dict[str, float], dict[str, list[str]]]:
    """Load allocations + groups from runtime symbol universe."""
    allocations: dict[str, float] = {}
    groups: dict[str, list[str]] = {}
    candidate_files = [
        (RUNTIME / "allocations_symbols.json", "allocations_symbols.json"),
        (RUNTIME / "allocations_override.json", "allocations_override.json"),
    ]
    for path, label in candidate_files:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            allocations = data.get("allocations", {}) or {}
            raw_groups = data.get("groups", {}) or {}
            groups = {k: list(v) for k, v in raw_groups.items()}
            if allocations:
                logger.info("Loaded allocation universe from %s", label)
                break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse %s: %s", label, exc)
            allocations = {}
            groups = {}
    return allocations, groups


def select_group(
    allocations: dict[str, float], groups: dict[str, list[str]], name: str
) -> dict[str, float]:
    """Pick weights for a named group."""
    symbols = groups.get(name, [])
    return {sym: allocations.get(sym, 0.0) for sym in symbols if allocations.get(sym, 0.0) > 0}


def fetch_weekly_metrics(symbols: Iterable[str]) -> dict[str, tuple[float | None, float | None]]:
    """Fetch last price and 5-session return for each symbol."""
    results: dict[str, tuple[float | None, float | None]] = dict.fromkeys(symbols, (None, None))
    if yf is None:
        return results

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d", interval="1d")
            if hist.empty:
                info = ticker.info
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                results[symbol] = (float(price) if price is not None else None, None)
                continue

            price = float(hist["Close"].iloc[-1])
            week_back_idx = -6 if len(hist) >= 6 else 0
            prior_price = float(hist["Close"].iloc[week_back_idx])
            weekly_return = None
            if prior_price and prior_price != 0:
                weekly_return = (price / prior_price - 1.0) * 100.0
            results[symbol] = (price, weekly_return)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Price fetch failed for %s: %s", symbol, exc)
    return results


def build_snapshot(weights: dict[str, float], top_n: int = 10) -> dict[str, object]:
    """Construct snapshot payload for a group."""
    ordered = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    metrics = fetch_weekly_metrics(sym for sym, _ in ordered[: top_n + 5])

    snapshots: list[SymbolSnapshot] = []
    for symbol, weight in ordered[:top_n]:
        price, weekly_return = metrics.get(symbol, (None, None))
        snapshots.append(SymbolSnapshot(symbol, weight, price, weekly_return))

    return {
        "total_weight": sum(weights.values()),
        "members": [
            {
                "symbol": snap.symbol,
                "weight": snap.weight,
                "weight_pct": snap.weight * 100.0,
                "price": snap.price,
                "weekly_return_pct": snap.weekly_return_pct,
            }
            for snap in snapshots
        ],
    }


def build_macro_snapshot(allocations: dict[str, float]) -> dict[str, object]:
    """Focus on commodity hedges (GLD, SLV, USO, TLT, IEF, PALL, PPLT)."""
    focus_symbols = ["GLD", "SLV", "USO", "TLT", "IEF", "PALL", "PPLT"]
    weights = {
        sym: allocations.get(sym, 0.0) for sym in focus_symbols if allocations.get(sym, 0.0) > 0
    }
    metrics = fetch_weekly_metrics(focus_symbols)
    members = []
    for symbol in focus_symbols:
        weight = weights.get(symbol, 0.0)
        price, weekly_return = metrics.get(symbol, (None, None))
        members.append(
            {
                "symbol": symbol,
                "weight": weight,
                "weight_pct": weight * 100.0,
                "price": price,
                "weekly_return_pct": weekly_return,
            }
        )
    return {
        "total_weight": sum(weights.values()),
        "members": members,
    }


def persist_plan(payload: dict[str, object]) -> None:
    """Write plan to state directory."""
    plan_file = STATE / "weekly_ai_rebalance_plan.json"
    plan_file.write_text(json.dumps(payload, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate weekly AI cohort & macro hedge snapshots."
    )
    parser.add_argument(
        "--macro-only",
        action="store_true",
        help="Only refresh macro/commodity tail-risk metrics.",
    )
    args = parser.parse_args()

    allocations, groups = load_allocations()
    if not allocations:
        logger.warning("No allocations available; skipping snapshot generation.")
        return 0

    payload: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "source": "weekly_ai_rebalance.py",
        "note": "Auto-generated weekly review for Guardian scheduler.",
    }

    if not args.macro_only:
        ai_weights = select_group(allocations, groups, "ai_rotation")
        payload["ai_rotation"] = build_snapshot(ai_weights)
    macro_snapshot = build_macro_snapshot(allocations)
    payload["macro_tail"] = macro_snapshot

    persist_plan(payload)
    logger.info("Weekly rebalance snapshot updated (macro_only=%s)", args.macro_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
