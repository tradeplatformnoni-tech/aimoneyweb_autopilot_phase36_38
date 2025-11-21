#!/usr/bin/env python3
"""
World-Class Health Check Framework
-----------------------------------
Standardized health check system for all agents and services.
"""

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """
    World-class health check system with metrics and history.

    Features:
    - Multiple health check functions
    - Automatic health monitoring
    - Health history tracking
    - Status aggregation
    - Metrics collection
    """

    def __init__(self, name: str, check_interval: float = 60.0):
        """
        Initialize health check.

        Args:
            name: Health check name
            check_interval: Interval between checks (seconds)
        """
        self.name = name
        self.check_interval = check_interval
        self._checks: list[Callable[[], dict[str, Any]]] = []
        self._status = HealthStatus.UNKNOWN
        self._last_check_time: float | None = None
        self._health_history: list[dict[str, Any]] = []
        self._metrics: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None

        # State directory
        self.state_dir = Path(os.path.expanduser("~/neolight/state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.health_file = self.state_dir / f"{name}_health.json"

        logger.info(f"🏥 Health check '{name}' initialized (interval={check_interval}s)")

    def add_check(self, check_func: Callable[[], dict[str, Any]], name: str | None = None):
        """
        Add a health check function.

        Args:
            check_func: Function that returns health status dict
            name: Optional name for the check
        """
        check_name = name or check_func.__name__
        wrapped = self._wrap_check(check_func, check_name)
        with self._lock:
            self._checks.append(wrapped)
        logger.debug(f"✅ Added health check '{check_name}' to '{self.name}'")

    def _wrap_check(self, check_func: Callable, name: str) -> Callable:
        """Wrap check function with error handling."""

        def wrapped():
            try:
                result = check_func()
                if not isinstance(result, dict):
                    result = {"status": "unknown", "message": "Invalid check result"}
                result["check_name"] = name
                result["timestamp"] = datetime.now(UTC).isoformat()
                return result
            except Exception as e:
                logger.error(f"❌ Health check '{name}' failed: {e}")
                return {
                    "check_name": name,
                    "status": "unhealthy",
                    "message": str(e),
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        return wrapped

    def check(self) -> dict[str, Any]:
        """
        Run all health checks and return aggregated status.

        Returns:
            Health status dictionary
        """
        with self._lock:
            self._last_check_time = time.time()

            if not self._checks:
                self._status = HealthStatus.UNKNOWN
                return {
                    "name": self.name,
                    "status": self._status.value,
                    "message": "No health checks configured",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            # Run all checks
            check_results = []
            healthy_count = 0
            degraded_count = 0
            unhealthy_count = 0

            for check_func in self._checks:
                result = check_func()
                check_results.append(result)

                status = result.get("status", "unknown")
                if status == "healthy":
                    healthy_count += 1
                elif status == "degraded":
                    degraded_count += 1
                elif status == "unhealthy":
                    unhealthy_count += 1

            # Aggregate status
            total_checks = len(check_results)
            if unhealthy_count > 0:
                self._status = HealthStatus.UNHEALTHY
            elif degraded_count > 0:
                self._status = HealthStatus.DEGRADED
            elif healthy_count == total_checks:
                self._status = HealthStatus.HEALTHY
            else:
                self._status = HealthStatus.UNKNOWN

            # Build result
            result = {
                "name": self.name,
                "status": self._status.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "checks": check_results,
                "summary": {
                    "total": total_checks,
                    "healthy": healthy_count,
                    "degraded": degraded_count,
                    "unhealthy": unhealthy_count,
                },
                "metrics": self._metrics.copy(),
            }

            # Save to history
            self._health_history.append(result)
            if len(self._health_history) > 100:  # Keep last 100 checks
                self._health_history = self._health_history[-100:]

            # Save to file
            self._save_health(result)

            return result

    def _save_health(self, health_data: dict[str, Any]):
        """Save health data to file."""
        try:
            self.health_file.write_text(json.dumps(health_data, indent=2))
        except Exception as e:
            logger.error(f"❌ Failed to save health data: {e}")

    def start_monitoring(self):
        """Start automatic health monitoring in background thread."""
        if self._running:
            logger.warning(f"⚠️ Health monitoring already running for '{self.name}'")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name=f"HealthCheck-{self.name}"
        )
        self._thread.start()
        logger.info(f"🏥 Started health monitoring for '{self.name}'")

    def stop_monitoring(self):
        """Stop automatic health monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"🛑 Stopped health monitoring for '{self.name}'")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                self.check()
            except Exception as e:
                logger.error(f"❌ Health check monitoring error: {e}")
            time.sleep(self.check_interval)

    def get_status(self) -> dict[str, Any]:
        """Get current health status."""
        with self._lock:
            return {
                "name": self.name,
                "status": self._status.value,
                "last_check": (
                    datetime.fromtimestamp(self._last_check_time, UTC).isoformat()
                    if self._last_check_time
                    else None
                ),
                "history_count": len(self._health_history),
                "metrics": self._metrics.copy(),
            }

    def update_metrics(self, metrics: dict[str, Any]):
        """Update health check metrics."""
        with self._lock:
            self._metrics.update(metrics)

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get health check history."""
        with self._lock:
            return self._health_history[-limit:]


# Convenience functions for common health checks


def check_process_running(process_name: str) -> dict[str, Any]:
    """Check if a process is running."""
    import psutil

    try:
        running = any(p.info["name"] == process_name for p in psutil.process_iter(["name"]))
        return {
            "status": "healthy" if running else "unhealthy",
            "message": f"Process '{process_name}' {'running' if running else 'not running'}",
        }
    except Exception as e:
        return {"status": "unhealthy", "message": f"Failed to check process: {e}"}


def check_file_exists(filepath: str, max_age: float | None = None) -> dict[str, Any]:
    """Check if a file exists and optionally check its age."""
    path = Path(filepath)

    if not path.exists():
        return {"status": "unhealthy", "message": f"File '{filepath}' does not exist"}

    if max_age:
        age = time.time() - path.stat().st_mtime
        if age > max_age:
            return {
                "status": "degraded",
                "message": f"File '{filepath}' is {age:.0f}s old (max: {max_age}s)",
            }

    return {"status": "healthy", "message": f"File '{filepath}' exists"}


def check_api_endpoint(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Check if an API endpoint is responding."""
    import requests

    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return {"status": "healthy", "message": f"API endpoint '{url}' responding"}
        else:
            return {
                "status": "degraded",
                "message": f"API endpoint '{url}' returned {response.status_code}",
            }
    except requests.Timeout:
        return {"status": "unhealthy", "message": f"API endpoint '{url}' timed out"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"API endpoint '{url}' error: {e}"}
