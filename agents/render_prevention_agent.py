#!/usr/bin/env python3
"""
Render Prevention Agent - Proactive Failure Prevention
======================================================
Prevents common failures before they occur:
- Resource monitoring (memory, CPU, disk)
- Dependency validation
- Configuration validation
- Health pre-checks
- Graceful degradation
"""

import json
import os
import psutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"

PREVENTION_STATE_FILE = STATE / "prevention_state.json"

# Resource thresholds
MEMORY_THRESHOLD_PCT = 85.0  # Alert if memory > 85%
CPU_THRESHOLD_PCT = 90.0  # Alert if CPU > 90%
DISK_THRESHOLD_PCT = 90.0  # Alert if disk > 90%


def check_resources() -> dict[str, Any]:
    """Check system resources."""
    resources = {
        "memory": {"used_pct": 0.0, "available_mb": 0, "status": "ok"},
        "cpu": {"used_pct": 0.0, "status": "ok"},
        "disk": {"used_pct": 0.0, "available_gb": 0, "status": "ok"},
    }

    try:
        # Memory
        mem = psutil.virtual_memory()
        resources["memory"]["used_pct"] = mem.percent
        resources["memory"]["available_mb"] = mem.available / (1024 * 1024)
        if mem.percent > MEMORY_THRESHOLD_PCT:
            resources["memory"]["status"] = "warning"

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        resources["cpu"]["used_pct"] = cpu_percent
        if cpu_percent > CPU_THRESHOLD_PCT:
            resources["cpu"]["status"] = "warning"

        # Disk
        disk = psutil.disk_usage(str(ROOT))
        resources["disk"]["used_pct"] = disk.percent
        resources["disk"]["available_gb"] = disk.free / (1024 * 1024 * 1024)
        if disk.percent > DISK_THRESHOLD_PCT:
            resources["disk"]["status"] = "warning"

    except Exception as e:
        print(f"[prevention] Resource check failed: {e}", flush=True)

    return resources


def validate_dependencies() -> dict[str, Any]:
    """Validate all required dependencies are available."""
    validation = {
        "status": "ok",
        "missing": [],
        "available": [],
    }

    required_modules = [
        "requests",
        "yfinance",
        "pandas",
        "numpy",
        "json",
        "pathlib",
    ]

    for module in required_modules:
        try:
            __import__(module)
            validation["available"].append(module)
        except ImportError:
            validation["missing"].append(module)
            validation["status"] = "error"

    return validation


def validate_configuration() -> dict[str, Any]:
    """Validate configuration."""
    config = {
        "status": "ok",
        "issues": [],
    }

    # Check RENDER_MODE
    if not RENDER_MODE:
        config["issues"].append("RENDER_MODE not set to true")
        config["status"] = "warning"

    # Check required paths
    required_paths = [
        ROOT / "agents",
        ROOT / "trader",
        ROOT / "backend",
    ]

    for path in required_paths:
        if not path.exists():
            config["issues"].append(f"Missing path: {path}")
            config["status"] = "error"

    return config


def apply_preventive_measures(resources: dict[str, Any], validation: dict[str, Any]) -> None:
    """Apply preventive measures based on checks."""
    # If memory is high, suggest cleanup
    if resources["memory"]["status"] == "warning":
        print(
            f"[prevention] ⚠️ High memory usage: {resources['memory']['used_pct']:.1f}%",
            flush=True,
        )
        # Could trigger log cleanup or reduce agent workload

    # If dependencies missing, try to install
    if validation["status"] == "error" and validation["missing"]:
        print(f"[prevention] ⚠️ Missing dependencies: {validation['missing']}", flush=True)
        # Could trigger auto-install


def main() -> None:
    """Main prevention loop."""
    print(
        f"[prevention] 🛡️ Render Prevention Agent starting @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    check_interval = int(os.getenv("PREVENTION_INTERVAL", "300"))  # Every 5 minutes

    while True:
        try:
            # Check resources
            resources = check_resources()

            # Validate dependencies
            dependencies = validate_dependencies()

            # Validate configuration
            configuration = validate_configuration()

            # Apply preventive measures
            apply_preventive_measures(resources, dependencies)

            # Save state
            state = {
                "last_check": datetime.now(UTC).isoformat(),
                "resources": resources,
                "dependencies": dependencies,
                "configuration": configuration,
            }
            try:
                PREVENTION_STATE_FILE.write_text(json.dumps(state, indent=2))
            except Exception:
                pass

            # Log summary
            all_ok = (
                resources["memory"]["status"] == "ok"
                and resources["cpu"]["status"] == "ok"
                and resources["disk"]["status"] == "ok"
                and dependencies["status"] == "ok"
                and configuration["status"] == "ok"
            )

            if all_ok:
                print("[prevention] ✅ All systems healthy", flush=True)
            else:
                print("[prevention] ⚠️ Some issues detected (see state file)", flush=True)

        except Exception as e:
            print(f"[prevention] ❌ Error: {e}", flush=True)

        time.sleep(check_interval)


if __name__ == "__main__":
    main()

