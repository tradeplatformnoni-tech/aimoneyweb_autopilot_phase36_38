#!/usr/bin/env python3
"""
Agent Self-Heal Orchestrator
============================

Purpose:
    - Enforce hygiene for the sports betting manual workflow (prune stale queue entries, ignore ancient predictions).
    - Monitor SmartTrader logs for data-source rate limits and trigger an automatic cooldown via guardian pause file.
    - Resume trading automatically once conditions stabilise.

This script is idempotent and safe to run on a cron/timer (e.g. every 10 minutes). It only touches files in `state/` and
`logs/` and never modifies code.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

SPORTS_QUEUE = STATE / "manual_bet_queue.json"
SPORTS_PREDICTIONS = STATE / "sports_predictions.json"
SMART_LOG = LOGS / "smart_trader.log"
GUARDIAN_PAUSE = STATE / "guardian_pause.json"

# Thresholds
RATE_LIMIT_THRESHOLD = (
    int(Path(ROOT / "state" / "self_heal_threshold.txt").read_text().strip())
    if (ROOT / "state" / "self_heal_threshold.txt").exists()
    else 20
)
COOLDOWN_MINUTES = (
    int(Path(ROOT / "state" / "self_heal_cooldown.txt").read_text().strip())
    if (ROOT / "state" / "self_heal_cooldown.txt").exists()
    else 5
)


def utc_now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Sports Betting Agent Hygiene
# ---------------------------------------------------------------------------


def heal_sports_agent() -> dict[str, Any]:
    """
    Prune stale manual queue entries and filter predictions so only near-term fixtures remain.
    Returns a summary dictionary.
    """
    from agents import sports_betting_agent as sports

    summary: dict[str, Any] = {
        "queue_before": 0,
        "queue_after": 0,
        "predictions_trimmed": 0,
    }

    queue = sports.load_queue()
    summary["queue_before"] = len(queue)
    queue = sports.prune_queue(queue)
    summary["queue_after"] = len(queue)
    if summary["queue_after"] != summary["queue_before"]:
        sports.save_json(SPORTS_QUEUE, queue)

    predictions = sports.load_json(SPORTS_PREDICTIONS, {})
    if isinstance(predictions, dict):
        trimmed = 0
        now = utc_now()
        for sport_key, payload in list(predictions.items()):
            if sport_key in {"timestamp", "last_update"}:
                continue
            entries = payload.get("predictions", [])
            filtered = []
            for entry in entries:
                scheduled = sports.parse_event_datetime(entry.get("scheduled"))
                if scheduled and now - timedelta(days=1) <= scheduled <= now + timedelta(days=10):
                    filtered.append(entry)
                else:
                    trimmed += 1
            payload["predictions"] = filtered
        if trimmed:
            sports.save_json(SPORTS_PREDICTIONS, predictions)
        summary["predictions_trimmed"] = trimmed

    return summary


# ---------------------------------------------------------------------------
# SmartTrader Rate Limit Monitor
# ---------------------------------------------------------------------------

RATE_LIMIT_PATTERNS = [
    re.compile(r"Too Many Requests", re.IGNORECASE),
    re.compile(r"Failed to fetch quote", re.IGNORECASE),
    re.compile(r"Could not fetch quote", re.IGNORECASE),
]


def count_rate_limit_events(log_text: str) -> int:
    total = 0
    for pattern in RATE_LIMIT_PATTERNS:
        total += len(pattern.findall(log_text))
    return total


def load_latest_log_segment(path: Path, max_bytes: int = 50_000) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if len(data) <= max_bytes:
        return data.decode(errors="ignore")
    return data[-max_bytes:].decode(errors="ignore")


def schedule_guardian_pause(reason: str, minutes: int) -> dict[str, Any]:
    until_dt = utc_now() + timedelta(minutes=minutes)
    payload = {
        "paused": True,
        "reason": reason,
        "until": until_dt.isoformat().replace("+00:00", "Z"),
        "updated_at": utc_now().isoformat().replace("+00:00", "Z"),
    }
    GUARDIAN_PAUSE.write_text(json.dumps(payload, indent=2))
    return {
        "paused": True,
        "until": payload["until"],
    }


def clear_guardian_pause(reason_prefix: str) -> bool:
    if not GUARDIAN_PAUSE.exists():
        return False
    try:
        payload = json.loads(GUARDIAN_PAUSE.read_text())
    except json.JSONDecodeError:
        GUARDIAN_PAUSE.unlink(missing_ok=True)
        return True
    if payload.get("paused") and payload.get("reason", "").startswith(reason_prefix):
        GUARDIAN_PAUSE.unlink(missing_ok=True)
        return True
    return False


def heal_smart_trader() -> dict[str, Any]:
    summary: dict[str, Any] = {
        "rate_limit_hits": 0,
        "cooldown_triggered": False,
        "cooldown_until": None,
        "cooldown_cleared": False,
    }

    log_tail = load_latest_log_segment(SMART_LOG)
    if not log_tail:
        return summary

    hit_count = count_rate_limit_events(log_tail)
    summary["rate_limit_hits"] = hit_count

    auto_reason = "Auto rate-limit cooldown"

    if hit_count >= RATE_LIMIT_THRESHOLD:
        pause_info = schedule_guardian_pause(auto_reason, COOLDOWN_MINUTES)
        summary["cooldown_triggered"] = True
        summary["cooldown_until"] = pause_info["until"]
    else:
        cleared = clear_guardian_pause(auto_reason)
        summary["cooldown_cleared"] = cleared

    return summary


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    result = {
        "timestamp": utc_now().isoformat().replace("+00:00", "Z"),
        "sports": heal_sports_agent(),
        "smart_trader": heal_smart_trader(),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
