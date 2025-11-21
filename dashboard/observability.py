#!/usr/bin/env python3
"""
Observability Dashboard - Real-Time System Health Visualization
================================================================
Provides real-time observability dashboard for system health, predictions, and metrics.

Features:
- Real-time system health visualization
- Failure prediction dashboard
- Anomaly detection alerts
- Trace visualization
- Metrics graphs
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)


def get_agent_status() -> dict[str, Any]:
    """Get current agent status."""
    status_file = STATE / "agent_status.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text())
        except Exception:
            return {}
    return {}


def get_failure_predictions() -> dict[str, Any]:
    """Get failure predictions."""
    predictions_file = STATE / "failure_predictions.json"
    if predictions_file.exists():
        try:
            return json.loads(predictions_file.read_text())
        except Exception:
            return {}
    return {}


def get_anomaly_detections() -> dict[str, Any]:
    """Get anomaly detections."""
    detections_file = STATE / "anomaly_detections.json"
    if detections_file.exists():
        try:
            return json.loads(detections_file.read_text())
        except Exception:
            return {}
    return {}


def get_metrics() -> dict[str, Any]:
    """Get metrics."""
    metrics_file = STATE / "metrics.json"
    if metrics_file.exists():
        try:
            return json.loads(metrics_file.read_text())
        except Exception:
            return {}
    return {}


def get_traces(limit: int = 100) -> list[dict[str, Any]]:
    """Get recent traces."""
    traces_file = STATE / "traces.json"
    if traces_file.exists():
        try:
            traces = json.loads(traces_file.read_text())
            if isinstance(traces, list):
                return traces[-limit:]
            return []
        except Exception:
            return []
    return []


def get_observability_summary() -> dict[str, Any]:
    """Get comprehensive observability summary."""
    agent_status = get_agent_status()
    predictions = get_failure_predictions()
    detections = get_anomaly_detections()
    metrics = get_metrics()

    # Calculate summary statistics
    total_agents = len(agent_status)
    healthy_agents = sum(1 for s in agent_status.values() if s.get("status") == "healthy")
    degraded_agents = sum(1 for s in agent_status.values() if s.get("status") == "degraded")
    stopped_agents = sum(1 for s in agent_status.values() if s.get("status") == "stopped")

    # Get high-risk predictions
    high_risk = {}
    if "predictions" in predictions:
        for agent, prob in predictions["predictions"].items():
            if prob > 0.7:
                high_risk[agent] = prob

    # Get active anomalies
    active_anomalies = {}
    if "detections" in detections:
        for agent, detection in detections["detections"].items():
            if detection.get("is_anomaly"):
                active_anomalies[agent] = detection

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "agents": {
            "total": total_agents,
            "healthy": healthy_agents,
            "degraded": degraded_agents,
            "stopped": stopped_agents,
            "health_percentage": (healthy_agents / total_agents * 100) if total_agents > 0 else 0,
        },
        "predictions": {
            "high_risk": high_risk,
            "total_predictions": len(predictions.get("predictions", {})),
        },
        "anomalies": {
            "active": len(active_anomalies),
            "details": active_anomalies,
        },
        "metrics": metrics.get("metrics", {}),
    }

