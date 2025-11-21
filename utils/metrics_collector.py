#!/usr/bin/env python3
"""
Metrics Collector - Prometheus-Compatible Metrics
==================================================
Collects and exposes metrics for monitoring.

Features:
- Prometheus-compatible metrics
- Custom metrics: agent health, error rates, recovery times, prediction accuracy
- Histograms for latency, resource usage
- Counters for events
"""

import json
import os
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Optional

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

METRICS_FILE = STATE / "metrics.json"

# Try to import Prometheus client
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    print("[metrics_collector] Prometheus client not available, using fallback", flush=True)


class SimpleMetrics:
    """Simple metrics implementation (fallback)."""

    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = Lock()

    def increment(self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None) -> None:
        """Increment a counter."""
        with self.lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self.counters[key] += value

    def set(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Set a gauge value."""
        with self.lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self.gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Observe a histogram value."""
        with self.lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self.histograms[key].append(value)
            # Keep only last 1000 observations
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        with self.lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {k: {
                    "count": len(v),
                    "sum": sum(v),
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                    "avg": sum(v) / len(v) if v else 0,
                } for k, v in self.histograms.items()},
            }


# Global metrics instance
_metrics: Optional[Any] = None
_simple_metrics = SimpleMetrics()


def get_metrics():
    """Get metrics instance."""
    global _metrics

    if _metrics is None:
        if HAS_PROMETHEUS:
            # Create Prometheus metrics
            _metrics = {
                "agent_health": Gauge("agent_health", "Agent health status", ["agent_name"]),
                "agent_errors_total": Counter("agent_errors_total", "Total agent errors", ["agent_name", "error_type"]),
                "agent_recovery_time": Histogram("agent_recovery_time_seconds", "Agent recovery time", ["agent_name"]),
                "failure_prediction_accuracy": Gauge("failure_prediction_accuracy", "Failure prediction accuracy", ["agent_name"]),
                "anomaly_detections_total": Counter("anomaly_detections_total", "Total anomaly detections", ["agent_name"]),
                "maintenance_actions_total": Counter("maintenance_actions_total", "Total maintenance actions", ["agent_name", "action_type"]),
                "system_cpu_usage": Gauge("system_cpu_usage_percent", "System CPU usage"),
                "system_memory_usage": Gauge("system_memory_usage_percent", "System memory usage"),
                "system_disk_usage": Gauge("system_disk_usage_percent", "System disk usage"),
            }
        else:
            _metrics = _simple_metrics

    return _metrics


def record_agent_health(agent_name: str, health: float) -> None:
    """Record agent health metric."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["agent_health"].labels(agent_name=agent_name).set(health)
    else:
        metrics.set("agent_health", health, {"agent_name": agent_name})


def record_agent_error(agent_name: str, error_type: str) -> None:
    """Record agent error."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["agent_errors_total"].labels(agent_name=agent_name, error_type=error_type).inc()
    else:
        metrics.increment("agent_errors_total", labels={"agent_name": agent_name, "error_type": error_type})


def record_recovery_time(agent_name: str, recovery_time_seconds: float) -> None:
    """Record agent recovery time."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["agent_recovery_time"].labels(agent_name=agent_name).observe(recovery_time_seconds)
    else:
        metrics.observe("agent_recovery_time", recovery_time_seconds, {"agent_name": agent_name})


def record_prediction_accuracy(agent_name: str, accuracy: float) -> None:
    """Record failure prediction accuracy."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["failure_prediction_accuracy"].labels(agent_name=agent_name).set(accuracy)
    else:
        metrics.set("failure_prediction_accuracy", accuracy, {"agent_name": agent_name})


def record_anomaly_detection(agent_name: str) -> None:
    """Record anomaly detection."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["anomaly_detections_total"].labels(agent_name=agent_name).inc()
    else:
        metrics.increment("anomaly_detections_total", labels={"agent_name": agent_name})


def record_maintenance_action(agent_name: str, action_type: str) -> None:
    """Record maintenance action."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["maintenance_actions_total"].labels(agent_name=agent_name, action_type=action_type).inc()
    else:
        metrics.increment("maintenance_actions_total", labels={"agent_name": agent_name, "action_type": action_type})


def record_system_resources(cpu: float, memory: float, disk: float) -> None:
    """Record system resource usage."""
    metrics = get_metrics()
    if HAS_PROMETHEUS:
        metrics["system_cpu_usage"].set(cpu)
        metrics["system_memory_usage"].set(memory)
        metrics["system_disk_usage"].set(disk)
    else:
        metrics.set("system_cpu_usage", cpu)
        metrics.set("system_memory_usage", memory)
        metrics.set("system_disk_usage", disk)


def get_metrics_prometheus_format() -> str:
    """Get metrics in Prometheus format."""
    if HAS_PROMETHEUS:
        return generate_latest(REGISTRY).decode("utf-8")
    else:
        # Convert simple metrics to Prometheus-like format
        metrics = _simple_metrics.get_metrics()
        lines = []
        for name, value in metrics["counters"].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in metrics["gauges"].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        for name, data in metrics["histograms"].items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {data['count']}")
            lines.append(f"{name}_sum {data['sum']}")
            lines.append(f"{name}_avg {data['avg']}")
        return "\n".join(lines)


def save_metrics() -> None:
    """Save metrics to file."""
    try:
        metrics_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": _simple_metrics.get_metrics() if not HAS_PROMETHEUS else {},
        }
        METRICS_FILE.write_text(json.dumps(metrics_data, indent=2))
    except Exception:
        pass


# Import for type hints
from typing import Optional

