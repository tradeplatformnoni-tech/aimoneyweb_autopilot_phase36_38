#!/usr/bin/env python3
"""
World-Class Structured Logging Framework
----------------------------------------
JSON-based structured logging with correlation IDs and context.
"""

import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add context if present
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
                "context",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""

    def __init__(self, correlation_id: str | None = None):
        super().__init__()
        self.correlation_id = correlation_id or str(uuid.uuid4())

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True


def setup_structured_logging(
    name: str,
    log_file: Path | None = None,
    level: int = logging.INFO,
    console: bool = True,
    correlation_id: str | None = None,
) -> logging.Logger:
    """
    Setup structured logging for a component.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level
        console: Enable console logging
        correlation_id: Optional correlation ID

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # Remove existing handlers

    # Create formatter
    formatter = StructuredFormatter()

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add correlation filter
    if correlation_id:
        correlation_filter = CorrelationFilter(correlation_id)
        logger.addFilter(correlation_filter)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: dict[str, Any] | None = None,
    correlation_id: str | None = None,
):
    """
    Log message with context.

    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        context: Optional context dictionary
        correlation_id: Optional correlation ID
    """
    extra = {}
    if context:
        extra["context"] = context
    if correlation_id:
        extra["correlation_id"] = correlation_id

    logger.log(level, message, extra=extra)
