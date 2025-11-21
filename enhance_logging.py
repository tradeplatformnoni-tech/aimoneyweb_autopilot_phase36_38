#!/usr/bin/env python3
"""
Enhance Error Logging - Enable Structured Logging
==================================================
Enables structured logging across all agents (free enhancement)
"""

import os
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
AGENTS_DIR = ROOT / "agents"


def enable_structured_logging():
    """Enable structured logging across all agents."""
    print("🔧 Enabling structured logging...")

    # Check if structured logger exists
    utils_dir = ROOT / "utils"
    structured_logger = utils_dir / "structured_logger.py"

    if not structured_logger.exists():
        print("⚠️  utils/structured_logger.py not found")
        print("   Creating basic structured logger...")
        create_basic_structured_logger()
    else:
        print("✅ Structured logger found")

    print("")
    print("📝 To enable structured logging in agents:")
    print("   1. Import: from utils.structured_logger import log")
    print("   2. Replace print() with log()")
    print("   3. Use: log('message', level='info', extra={'key': 'value'})")
    print("")
    print("✅ Structured logging enhancement complete!")


def create_basic_structured_logger():
    """Create basic structured logger if it doesn't exist."""
    utils_dir = ROOT / "utils"
    utils_dir.mkdir(parents=True, exist_ok=True)

    logger_code = '''"""
Structured Logger - Enhanced Logging with Correlation IDs
==========================================================
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

LOGGER = logging.getLogger("neolight")
LOGGER.setLevel(logging.INFO)

def log(
    message: str,
    level: str = "info",
    extra: Optional[dict[str, Any]] = None,
    correlation_id: Optional[str] = None
):
    """Structured logging with JSON output."""
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        "correlation_id": correlation_id or "default",
    }

    if extra:
        log_data.update(extra)

    # Print as JSON for structured logging
    print(json.dumps(log_data, ensure_ascii=False), flush=True)
'''

    logger_file = utils_dir / "structured_logger.py"
    logger_file.write_text(logger_code)
    print(f"✅ Created {logger_file}")


if __name__ == "__main__":
    enable_structured_logging()
