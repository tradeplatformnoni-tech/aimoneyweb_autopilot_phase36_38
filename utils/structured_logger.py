#!/usr/bin/env python3
"""
Structured Logger - JSON-Structured Logging with Correlation IDs
==================================================================
Provides structured logging with correlation IDs for request tracking.

Features:
- JSON-structured logs with correlation IDs
- Log levels, timestamps, context
- Centralized log aggregation
- Log querying and analysis
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
LOGS = ROOT / "logs"

LOGS.mkdir(parents=True, exist_ok=True)

# Import correlation ID from tracing
try:
    from utils.tracing import get_correlation_id
except ImportError:
    def get_correlation_id() -> str:
        import uuid
        return str(uuid.uuid4())


class StructuredLogger:
    """Structured logger with correlation IDs."""

    def __init__(self, name: str, log_file: Optional[Path] = None):
        self.name = name
        self.log_file = log_file or (LOGS / f"{name}.jsonl")
        self.correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for this logger instance."""
        self.correlation_id = correlation_id

    def _log(self, level: str, message: str, **kwargs) -> None:
        """Internal logging method."""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            "correlation_id": self.correlation_id or get_correlation_id(),
        }

        # Add any additional context
        log_entry.update(kwargs)

        # Write to JSONL file
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass

        # Also print to stdout for compatibility
        print(f"[{level}] [{self.name}] {message}", flush=True)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log("CRITICAL", message, **kwargs)

    def exception(self, message: str, exc_info: Any = None, **kwargs) -> None:
        """Log exception."""
        import traceback
        kwargs["exception"] = traceback.format_exc()
        self._log("ERROR", message, **kwargs)


def get_logger(name: str, log_file: Optional[Path] = None) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name, log_file)


# Convenience function for backward compatibility
def log(level: str, message: str, logger_name: str = "default", **kwargs) -> None:
    """Convenience logging function."""
    logger = get_logger(logger_name)
    getattr(logger, level.lower())(message, **kwargs)

