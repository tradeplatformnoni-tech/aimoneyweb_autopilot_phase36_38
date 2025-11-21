#!/usr/bin/env python3
"""
Atlas Bridge Agent - Phase 900-1100
Supervises dashboard updates and telemetry snapshots
Links Dashboard V3 → Orchestrator via REST API
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT = Path(os.path.expanduser("~/neolight"))
RUNTIME = ROOT / "runtime"
STATE = ROOT / "state"
DATA = ROOT / "data"
TELEMETRY_DIR = DATA / "telemetry"
LOGS = ROOT / "logs"

for d in [RUNTIME, STATE, DATA, TELEMETRY_DIR, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# Detect Render environment - disable dashboard on Render (no localhost)
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
DASHBOARD_URL = os.getenv(
    "NEOLIGHT_DASHBOARD_URL", "http://localhost:8100" if not RENDER_MODE else None
)
UPDATE_INTERVAL = int(os.getenv("ATLAS_BRIDGE_INTERVAL", "30"))


def fetch_orchestrator_state() -> dict[str, Any] | None:
    """Fetch current brain state from orchestrator outputs."""
    try:
        brain_file = RUNTIME / "atlas_brain.json"
        if brain_file.exists():
            return json.loads(brain_file.read_text())
    except Exception as e:
        print(f"[atlas_bridge] Error reading brain: {e}", flush=True)
    return None


def fetch_allocations() -> dict[str, Any] | None:
    """Fetch current allocations from weights_bridge."""
    try:
        alloc_file = RUNTIME / "allocations_override.json"
        if alloc_file.exists():
            return json.loads(alloc_file.read_text())
    except Exception as e:
        print(f"[atlas_bridge] Error reading allocations: {e}", flush=True)
    return None


def push_to_dashboard(data: dict[str, Any]) -> bool:
    """Push data to dashboard via REST API."""
    if not DASHBOARD_URL:
        # On Render, skip dashboard push (no localhost available)
        return True
    try:
        response = requests.post(f"{DASHBOARD_URL}/atlas/update", json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[atlas_bridge] Dashboard push failed: {e}", flush=True)
        return False


def push_meta_metrics(data: dict[str, Any]) -> bool:
    """Push meta-metrics to dashboard (Phase 5600)."""
    if not DASHBOARD_URL:
        # On Render, skip dashboard push (no localhost available)
        return True
    try:
        response = requests.post(f"{DASHBOARD_URL}/meta/metrics", json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[atlas_bridge] Meta-metrics push failed: {e}", flush=True)
        return False


def create_telemetry_snapshot() -> None:
    """Create timestamped telemetry snapshot."""
    try:
        brain = fetch_orchestrator_state()
        allocs = fetch_allocations()

        snapshot = {
            "timestamp": datetime.now(UTC).isoformat(),
            "brain": brain or {},
            "allocations": allocs or {},
            "system": {
                "cpu": os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0,
                "memory_mb": 0,  # psutil would be better here
            },
        }

        snapshot_file = (
            TELEMETRY_DIR / f"snapshot_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )
        snapshot_file.write_text(json.dumps(snapshot, indent=2))
        print(f"[atlas_bridge] Snapshot saved: {snapshot_file.name}", flush=True)
    except Exception as e:
        print(f"[atlas_bridge] Snapshot error: {e}", flush=True)
        traceback.print_exc()


def main() -> None:
    """Main bridge loop: fetch orchestrator data, push to dashboard, create snapshots."""
    print(
        f"[atlas_bridge] Starting bridge loop @ {datetime.now(UTC).isoformat()}Z; interval={UPDATE_INTERVAL}s",
        flush=True,
    )

    snapshot_counter = 0
    while True:
        try:
            brain = fetch_orchestrator_state()
            allocs = fetch_allocations()

            if brain or allocs:
                bridge_data = {
                    "brain": brain,
                    "allocations": allocs,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                # Push to dashboard
                push_to_dashboard(bridge_data)

                # Create snapshot every 10 cycles (~5 minutes at 30s interval)
                snapshot_counter += 1
                if snapshot_counter >= 10:
                    create_telemetry_snapshot()
                    snapshot_counter = 0

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("[atlas_bridge] Shutting down gracefully...", flush=True)
            break
        except Exception as e:
            print(f"[atlas_bridge] Loop error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
