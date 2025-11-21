#!/usr/bin/env python3
"""
Phase 3900-4100: Event-Driven Architecture - Enhanced
------------------------------------------------------
Real-time signal processing and event handling with comprehensive event capture.
"""

import json
import logging
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "event_driven.log"
EVENTS_FILE = STATE / "event_stream.json"
MAX_EVENTS = 1000  # Keep last 1000 events

logger = logging.getLogger("event_driven")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)


def process_event(event_type: str, data: dict, source: str | None = None) -> dict[str, Any]:
    """
    Process and store trading events.

    Args:
        event_type: Type of event (e.g., "BUY", "SELL", "REGIME_CHANGE", "RISK_BREACH")
        data: Event data dictionary
        source: Source of the event (e.g., "smart_trader", "regime_detector", "risk_governor")

    Returns:
        Event dictionary
    """
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "type": event_type,
        "source": source or "unknown",
        "data": data,
    }

    try:
        # Load existing events
        events = []
        if EVENTS_FILE.exists():
            try:
                events = json.loads(EVENTS_FILE.read_text())
                if not isinstance(events, list):
                    events = []
            except Exception as e:
                logger.warning(f"⚠️  Error loading events: {e}")
                events = []

        events.append(event)

        # Keep last N events
        if len(events) > MAX_EVENTS:
            events = events[-MAX_EVENTS:]

        # Save events
        EVENTS_FILE.write_text(json.dumps(events, indent=2))
        logger.debug(f"📊 Event recorded: {event_type} from {source}")

        return event

    except Exception as e:
        logger.error(f"❌ Error processing event: {e}")
        traceback.print_exc()
        return event


def get_recent_events(event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Get recent events, optionally filtered by type."""
    if not EVENTS_FILE.exists():
        return []

    try:
        events = json.loads(EVENTS_FILE.read_text())
        if not isinstance(events, list):
            return []

        # Filter by type if specified
        if event_type:
            events = [e for e in events if e.get("type") == event_type]

        # Return most recent
        return events[-limit:]

    except Exception as e:
        logger.warning(f"⚠️  Error reading events: {e}")
        return []


def get_event_summary() -> dict[str, Any]:
    """Get summary of recent events."""
    events = get_recent_events(limit=MAX_EVENTS)

    if not events:
        return {"total_events": 0, "event_counts": {}, "latest_event": None}

    # Count events by type
    event_counts = {}
    for event in events:
        event_type = event.get("type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    return {
        "total_events": len(events),
        "event_counts": event_counts,
        "latest_event": events[-1] if events else None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def monitor_trading_events():
    """Monitor and process trading events from various sources."""
    pnl_file = STATE / "pnl_history.csv"
    last_trade_time = None

    while True:
        try:
            # Monitor trade file for new trades
            if pnl_file.exists():
                try:
                    with open(pnl_file) as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # Has header + at least one trade
                            last_line = lines[-1].strip()
                            if last_line and last_line != last_trade_time:
                                # New trade detected - parse it
                                parts = last_line.split(",")
                                if len(parts) >= 4:
                                    timestamp = parts[0]
                                    symbol = parts[1] if len(parts) > 1 else "UNKNOWN"
                                    side = parts[2] if len(parts) > 2 else "UNKNOWN"

                                    if side.upper() in ["BUY", "SELL"]:
                                        process_event(
                                            side.upper(),
                                            {
                                                "symbol": symbol,
                                                "timestamp": timestamp,
                                                "source_file": "pnl_history.csv",
                                            },
                                            source="trade_monitor",
                                        )
                                        last_trade_time = last_line
                except Exception as e:
                    logger.debug(f"Trade monitoring: {e}")

            time.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"❌ Error monitoring trades: {e}")
            time.sleep(30)


def main():
    """Main event-driven architecture loop."""
    logger.info("🚀 Event-Driven Architecture starting...")

    # Initialize event stream
    process_event(
        "system_start", {"message": "Event-driven architecture initialized"}, source="event_system"
    )

    # Start trade monitoring in background (simplified - would use threading/async in production)
    import threading

    monitor_thread = threading.Thread(target=monitor_trading_events, daemon=True)
    monitor_thread.start()

    update_interval = int(os.getenv("NEOLIGHT_EVENT_INTERVAL", "60"))  # Default 1 minute

    while True:
        try:
            # Generate event summary periodically
            summary = get_event_summary()

            if summary["total_events"] > 0:
                logger.info(
                    f"📊 Events: {summary['total_events']} total, types: {list(summary['event_counts'].keys())}"
                )

            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Event-Driven Architecture stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in event loop: {e}")
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
