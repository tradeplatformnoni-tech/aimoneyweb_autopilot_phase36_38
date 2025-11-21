#!/usr/bin/env python3
"""
NeoLight Sports Model Report
============================

Summarises the latest predictions stored under ``state/sports_predictions_*.json``
so we can review edge, confidence, and model accuracy/CLV metrics per sport.

Usage
-----
    PYTHONPATH=~/neolight venv/bin/python analytics/sports_model_report.py --sport nba
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path.home() / "neolight"
STATE = ROOT / "state"


def load_predictions(sport: str) -> dict[str, Any]:
    """Load the most recent prediction payload for a given sport."""
    primary_path = STATE / f"sports_predictions_{sport.lower()}.json"
    fallback_path = STATE / "sports_predictions.json"

    if primary_path.exists():
        return json.loads(primary_path.read_text())

    if fallback_path.exists():
        data = json.loads(fallback_path.read_text())
        # Some aggregated files are structured as {"nba": {...}, "nfl": {...}}
        if sport.lower() in data:
            return data[sport.lower()]
        return data

    raise FileNotFoundError(
        f"No prediction file found for sport '{sport}'. Expected {primary_path} or {fallback_path}."
    )


def safe_datetime(value: str) -> datetime | None:
    """Parse ISO timestamps, returning None if invalid."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def summarise_predictions(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute summary statistics for the prediction payload."""
    predictions = payload.get("predictions", [])
    if not predictions:
        return {
            "prediction_count": 0,
            "avg_edge": 0.0,
            "avg_confidence": 0.0,
            "avg_clv": 0.0,
            "max_edge": 0.0,
            "upcoming_games": 0,
            "regime_distribution": {},
            "top_predictions": [],
        }

    edges = [p.get("edge", 0.0) for p in predictions]
    confidences = [p.get("confidence", 0.0) for p in predictions]
    clvs = [p.get("clv_estimate", 0.0) for p in predictions if p.get("clv_estimate") is not None]
    regimes = Counter(p.get("regime", "unknown") for p in predictions)

    now = datetime.now(UTC)
    upcoming = sum(
        1
        for p in predictions
        if (dt := safe_datetime(p.get("scheduled"))) is not None and dt >= now
    )

    return {
        "prediction_count": len(predictions),
        "avg_edge": statistics.fmean(edges) if edges else 0.0,
        "avg_confidence": statistics.fmean(confidences) if confidences else 0.0,
        "avg_clv": statistics.fmean(clvs) if clvs else 0.0,
        "max_edge": max(edges) if edges else 0.0,
        "upcoming_games": upcoming,
        "regime_distribution": dict(regimes.most_common()),
        "top_predictions": sorted(
            predictions,
            key=lambda p: p.get("edge", 0.0),
            reverse=True,
        )[:5],
    }


def summarise_models(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull model accuracy/log-loss statistics."""
    metadata = payload.get("model", {}).get("metadata", [])
    if not metadata:
        return {}

    sorted_models = sorted(metadata, key=lambda m: m.get("accuracy", 0.0), reverse=True)
    top_model = sorted_models[0]

    return {
        "top_model": top_model,
        "all_models": sorted_models[:5],
    }


def format_report(sport: str, payload: dict[str, Any]) -> str:
    """Render a human-readable report."""
    summary = summarise_predictions(payload)
    model_info = summarise_models(payload)

    lines: list[str] = []
    lines.append(f"=== Sports Model Report :: {sport.upper()} ===")
    lines.append(f"Timestamp: {payload.get('timestamp', 'unknown')}")
    lines.append(f"Predictions: {summary['prediction_count']}")
    lines.append(f"Upcoming games: {summary['upcoming_games']}")
    lines.append(f"Average edge: {summary['avg_edge'] * 100:.2f}%")
    lines.append(f"Average confidence: {summary['avg_confidence'] * 100:.2f}%")
    lines.append(f"Average CLV estimate: {summary['avg_clv'] * 100:.2f}%")
    lines.append(f"Max edge: {summary['max_edge'] * 100:.2f}%")

    if summary["regime_distribution"]:
        lines.append("Regime distribution:")
        for regime, count in summary["regime_distribution"].items():
            lines.append(f"  - {regime}: {count}")

    if model_info:
        lines.append("Top models (accuracy/log-loss):")
        for model in model_info["all_models"]:
            lines.append(
                f"  - {model.get('name', 'unknown')}: "
                f"{model.get('accuracy', 0.0) * 100:.2f}% | "
                f"logloss {model.get('log_loss', 0.0):.4f}"
            )

    if summary["top_predictions"]:
        lines.append("Top edges:")
        for pred in summary["top_predictions"]:
            lines.append(
                f"  - {pred.get('recommended_side')} vs {pred.get('away_team')} "
                f"({pred.get('edge', 0) * 100:.2f}% edge, confidence {pred.get('confidence', 0) * 100:.2f}%) "
                f"scheduled {pred.get('scheduled')}"
            )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sports model summary.")
    parser.add_argument("--sport", required=True, help="Sport code (e.g. nba, nfl, mlb, soccer).")
    args = parser.parse_args()

    payload = load_predictions(args.sport)
    report = format_report(args.sport, payload)
    print(report)


if __name__ == "__main__":
    main()
