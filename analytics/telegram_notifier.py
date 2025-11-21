"""Telegram notification helper for sports betting system."""

from __future__ import annotations

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a Telegram alert message.

    Args:
        message: The message text to send
        parse_mode: Telegram parse mode (Markdown or HTML)

    Returns:
        True if message sent successfully, False otherwise
    """
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False

    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode,
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def alert_stale_data(sport: str, data_type: str, hours_old: int, threshold_hours: int) -> None:
    """Alert when sports data becomes stale."""
    message = f"""⚠️ **Stale Data Alert**

**Sport**: {sport.upper()}
**Type**: {data_type}
**Age**: {hours_old} hours
**Threshold**: {threshold_hours} hours

Please run ingestion to refresh data.
"""
    send_alert(message)


def alert_ingestion_failure(sport: str, script: str, error: str | None = None) -> None:
    """Alert when sports data ingestion fails."""
    message = f"""❌ **Ingestion Failure**

**Sport**: {sport.upper()}
**Script**: {script}
"""
    if error:
        message += f"**Error**: {error}\n"

    message += "\nCheck logs for details."
    send_alert(message)


def alert_missing_data(sport: str, data_type: str, expected_path: str) -> None:
    """Alert when expected data files are missing."""
    message = f"""⚠️ **Missing Data Alert**

**Sport**: {sport.upper()}
**Type**: {data_type}
**Expected Path**: {expected_path}

Data directory or files not found.
"""
    send_alert(message)


def alert_prediction_ready(sport: str, edge_count: int, accuracy: float | None = None) -> None:
    """Alert when new predictions are ready."""
    message = f"""✅ **Predictions Ready**

**Sport**: {sport.upper()}
**Edges Found**: {edge_count}
"""
    if accuracy:
        message += f"**Model Accuracy**: {accuracy * 100:.1f}%\n"

    message += "\nCheck dashboard or state files for details."
    send_alert(message)


__all__ = [
    "send_alert",
    "alert_stale_data",
    "alert_ingestion_failure",
    "alert_missing_data",
    "alert_prediction_ready",
]
