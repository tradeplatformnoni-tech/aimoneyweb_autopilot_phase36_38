#!/usr/bin/env python3
"""Guardian job definitions for sports analytics pipeline.

This module defines scheduled jobs for nightly data ingestion, arbitrage scanning,
and data staleness monitoring. Import these into your Guardian orchestrator.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
LOGS = ROOT / "logs"
DATA = ROOT / "data"


def run_command(cmd: str, description: str) -> dict[str, Any]:
    """Execute a shell command and return status."""
    print(f"[guardian] Starting: {description}", flush=True)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes
        )
        if result.returncode == 0:
            print(f"[guardian] ✅ {description} completed", flush=True)
            return {"status": "success", "output": result.stdout}
        else:
            print(f"[guardian] ❌ {description} failed: {result.stderr}", flush=True)
            return {"status": "error", "error": result.stderr}
    except subprocess.TimeoutExpired:
        print(f"[guardian] ⏱️ {description} timed out", flush=True)
        return {"status": "timeout"}
    except Exception as exc:
        print(f"[guardian] 💥 {description} exception: {exc}", flush=True)
        return {"status": "exception", "error": str(exc)}


def ingest_nba_data() -> dict[str, Any]:
    """Scheduled job: Ingest NBA schedule, odds, and injuries."""
    cmd = (
        f"cd {ROOT} && "
        "source venv/bin/activate && "
        "export PYTHONPATH=$(pwd) && "
        "set -a && . ./.env && set +a && "
        "python scripts/ingest_nba_data.py --seasons 2024,2023"
    )
    return run_command(cmd, "NBA data ingestion")


def ingest_soccer_data() -> dict[str, Any]:
    """Scheduled job: Ingest soccer fixtures and odds."""
    cmd = (
        f"cd {ROOT} && "
        "source venv/bin/activate && "
        "export PYTHONPATH=$(pwd) && "
        "set -a && . ./.env && set +a && "
        "python scripts/ingest_soccer_data.py --seasons 2024,2023 --leagues EPL,LaLiga --odds"
    )
    return run_command(cmd, "Soccer data ingestion")


def generate_predictions() -> dict[str, Any]:
    """Scheduled job: Run analytics agent to produce predictions."""
    cmd = (
        f"cd {ROOT} && "
        "source venv/bin/activate && "
        "export PYTHONPATH=$(pwd) && "
        "set -a && . ./.env && set +a && "
        "timeout 600 python agents/sports_analytics_agent.py"  # 10-minute limit
    )
    return run_command(cmd, "Sports predictions generation")


def scan_arbitrage() -> dict[str, Any]:
    """Scheduled job: Scan local odds for arbitrage opportunities."""
    cmd = (
        f"cd {ROOT} && "
        "source venv/bin/activate && "
        "export PYTHONPATH=$(pwd) && "
        "set -a && . ./.env && set +a && "
        "timeout 120 python agents/sports_arbitrage_agent.py"  # single-pass scan
    )
    # For continuous monitoring, remove timeout and let it run as daemon
    return run_command(cmd, "Arbitrage scan")


def check_data_staleness() -> dict[str, Any]:
    """Scheduled job: Alert if data hasn't been refreshed recently."""
    import json

    stale_threshold = timedelta(hours=36)
    now = datetime.utcnow()
    issues: list[str] = []

    # Check odds snapshots
    for sport in ("nba", "soccer"):
        odds_dir = DATA / "odds_snapshots" / sport
        if not odds_dir.exists():
            issues.append(f"{sport} odds directory missing")
            continue
        files = sorted(odds_dir.glob("*.json"))
        if not files:
            issues.append(f"No {sport} odds snapshots")
            continue
        latest = files[-1]
        age = now - datetime.fromtimestamp(latest.stat().st_mtime)
        if age > stale_threshold:
            issues.append(f"{sport} odds stale ({age.total_seconds() / 3600:.1f}h old)")

    # Check predictions
    predictions_file = STATE / "sports_predictions.json"
    if predictions_file.exists():
        try:
            data = json.loads(predictions_file.read_text())
            last_update = data.get("last_update")
            if last_update:
                pred_time = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                age = now - pred_time.replace(tzinfo=None)
                if age > stale_threshold:
                    issues.append(f"Predictions stale ({age.total_seconds() / 3600:.1f}h old)")
        except (json.JSONDecodeError, ValueError):
            issues.append("Predictions file corrupted")
    else:
        issues.append("No predictions file found")

    if issues:
        alert = "⚠️ *Data Staleness Alert*\n" + "\n".join(f"• {issue}" for issue in issues)
        send_telegram(alert)
        return {"status": "stale", "issues": issues}

    print("[guardian] ✅ All data fresh", flush=True)
    return {"status": "fresh"}


def send_telegram(message: str) -> None:
    """Send Telegram alert."""
    import os

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("[guardian] Telegram credentials missing", flush=True)
        return

    try:
        import requests

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"[guardian] Telegram failed: {response.text}", flush=True)
    except Exception as exc:
        print(f"[guardian] Telegram error: {exc}", flush=True)


# Job schedule definitions (cron-style or interval-based)
GUARDIAN_JOBS = {
    "nba_ingestion": {
        "function": ingest_nba_data,
        "schedule": "0 2 * * *",  # 2 AM daily
        "description": "Fetch NBA schedules, odds, injuries",
    },
    "soccer_ingestion": {
        "function": ingest_soccer_data,
        "schedule": "0 3 * * *",  # 3 AM daily
        "description": "Fetch soccer fixtures and odds",
    },
    "predictions_generation": {
        "function": generate_predictions,
        "schedule": "0 4 * * *",  # 4 AM daily (after ingestion)
        "description": "Generate predictions from latest data",
    },
    "arbitrage_scan": {
        "function": scan_arbitrage,
        "schedule": "*/30 * * * *",  # Every 30 minutes
        "description": "Scan for arbitrage opportunities",
    },
    "staleness_check": {
        "function": check_data_staleness,
        "schedule": "0 */6 * * *",  # Every 6 hours
        "description": "Check if data needs refresh",
    },
}


if __name__ == "__main__":
    """CLI for running individual jobs."""
    if len(sys.argv) < 2:
        print("Usage: python guardian_sports_jobs.py <job_name>")
        print("Available jobs:", ", ".join(GUARDIAN_JOBS.keys()))
        sys.exit(1)

    job_name = sys.argv[1]
    job = GUARDIAN_JOBS.get(job_name)
    if not job:
        print(f"Unknown job: {job_name}")
        sys.exit(1)

    result = job["function"]()
    print(f"Result: {result}")
    sys.exit(0 if result.get("status") in ("success", "fresh") else 1)
