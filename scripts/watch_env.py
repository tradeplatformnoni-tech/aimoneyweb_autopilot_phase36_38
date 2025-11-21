#!/usr/bin/env python3
"""
.env Watcher + Auto-Restart
===========================
Computes the SHA256 hash of `.env`, stores it under state/env_hash.json, and
triggers a controlled restart (with logging + Telegram alert) whenever the file
changes. Keeps SmartTrader and supporting agents in sync with the latest API
keys/feature flags.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import requests

    HAS_REQUESTS = True
except ImportError:  # pragma: no cover
    HAS_REQUESTS = False

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)
HASH_FILE = STATE_DIR / "env_hash.json"
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "guardian.log"

# Processes spawned by launch_all.sh that should be restarted
PROCESS_PATTERNS = [
    "trader/smart_trader.py",
    "agents/guardian_agent.py",
    "agents/sports_betting_agent.py",
    "phases/phase_41_50_atlas_dashboard.sh",
    "phases/phase_81_90_atlas_feedback.sh",
    "phases/phase_91_100_neural_tuner.py",
    "phases/phase_101_120_risk_governor.sh",
    "phases/phase_121_130_drawdown_guard.sh",
    "phases/phase_131_140_allocator.py",
    "scripts/rclone_sync.sh",
]


def utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    line = f"[{utc_timestamp()}] {message}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def compute_env_hash() -> str:
    data = b""
    if ENV_FILE.exists():
        data = ENV_FILE.read_bytes()
    return hashlib.sha256(data).hexdigest()


def read_last_hash() -> str | None:
    if not HASH_FILE.exists():
        return None
    try:
        payload = json.loads(HASH_FILE.read_text())
        return payload.get("sha256")
    except Exception:
        return None


def persist_hash(value: str) -> None:
    payload = {"sha256": value, "updated": utc_timestamp()}
    HASH_FILE.write_text(json.dumps(payload, indent=2))


def send_telegram(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id and HAS_REQUESTS):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=5,
        )
    except Exception as exc:  # pragma: no cover
        log(f"⚠️ Telegram notification failed: {exc}")


def stop_processes() -> None:
    for pattern in PROCESS_PATTERNS:
        subprocess.run(["pkill", "-f", pattern], check=False)


def restart_stack() -> bool:
    cmd = f"cd {ROOT} && bash launch_all.sh"
    result = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        if result.stdout:
            log(result.stdout.strip())
        return True
    log(f"❌ launch_all.sh failed (exit {result.returncode}): {result.stderr.strip()}")
    return False


def main() -> None:
    current_hash = compute_env_hash()
    last_hash = read_last_hash()

    if last_hash is None:
        persist_hash(current_hash)
        log("Initialized .env hash tracker.")
        return

    if current_hash == last_hash:
        return

    log(f".env change detected (sha256 {last_hash[:8]} → {current_hash[:8]}).")
    send_telegram("📦 .env changed on NeoLight host — restarting stack.")

    stop_processes()
    if restart_stack():
        log("✅ Stack relaunched via launch_all.sh")
        send_telegram("✅ Stack relaunched after .env change.")
    else:
        send_telegram("❌ Failed to relaunch stack after .env change.")

    persist_hash(current_hash)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"❌ watch_env.py crashed: {exc}")
        sys.exit(1)
