#!/usr/bin/env python3
"""
Phase 1-50: Foundation & System Initialization - WORLD CLASS
===========================================================
Einstein-level foundation system with:
- Configuration management (env vars, config files, validation)
- System health monitoring
- Resource management (memory, CPU, disk)
- Graceful startup/shutdown
- Dependency validation
- State persistence
- Paper-mode compatibility
"""

import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
CONFIG = ROOT / "config"
for p in [STATE, RUNTIME, LOGS, CONFIG]:
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "foundation.log"
logger = logging.getLogger("foundation")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    from utils.circuit_breaker import CircuitBreaker
    from utils.health_check import HealthCheck
    from utils.retry import retry_with_backoff
    from utils.state_manager import StateManager

    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False
    logger.warning("⚠️ World-class utilities not available")

CONFIG_FILE = CONFIG / "system_config.json"
SYSTEM_STATE_FILE = STATE / "system_state.json"


class FoundationManager:
    """World-class foundation system manager."""

    def __init__(self):
        """Initialize foundation manager."""
        self.config = self.load_config()
        self.state_manager = None
        if HAS_WORLD_CLASS_UTILS:
            try:
                self.state_manager = StateManager(
                    SYSTEM_STATE_FILE,
                    default_state={"startup_time": datetime.now(UTC).isoformat()},
                    backup_count=24,
                    backup_interval=3600.0,
                )
            except Exception as e:
                logger.warning(f"⚠️ StateManager init failed: {e}")
        logger.info("✅ FoundationManager initialized")

    def load_config(self) -> dict[str, Any]:
        """Load system configuration with validation."""
        default_config = {
            "trading_mode": os.getenv("NEOLIGHT_TRADING_MODE", "PAPER_TRADING_MODE"),
            "max_memory_mb": int(os.getenv("NEOLIGHT_MAX_MEMORY_MB", "4096")),
            "max_cpu_percent": int(os.getenv("NEOLIGHT_MAX_CPU_PERCENT", "80")),
            "health_check_interval": int(os.getenv("NEOLIGHT_HEALTH_CHECK_INTERVAL", "60")),
            "log_level": os.getenv("NEOLIGHT_LOG_LEVEL", "INFO"),
            "enable_telemetry": os.getenv("NEOLIGHT_ENABLE_TELEMETRY", "true").lower() == "true",
        }

        if CONFIG_FILE.exists():
            try:
                file_config = json.loads(CONFIG_FILE.read_text())
                default_config.update(file_config)
            except Exception as e:
                logger.warning(f"⚠️ Error loading config file: {e}")

        return default_config

    def validate_dependencies(self) -> dict[str, bool]:
        """Validate all system dependencies."""
        dependencies = {
            "numpy": False,
            "pandas": False,
            "yfinance": False,
            "psutil": True,  # Already imported
        }

        for dep in ["numpy", "pandas", "yfinance"]:
            try:
                __import__(dep)
                dependencies[dep] = True
            except ImportError:
                dependencies[dep] = False

        return dependencies

    def check_system_resources(self) -> dict[str, Any]:
        """Check system resource usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=1.0)

            return {
                "memory_mb": memory_info.rss / 1024 / 1024,
                "cpu_percent": cpu_percent,
                "disk_usage": {
                    "total_gb": psutil.disk_usage(str(ROOT)).total / 1024 / 1024 / 1024,
                    "used_gb": psutil.disk_usage(str(ROOT)).used / 1024 / 1024 / 1024,
                    "free_gb": psutil.disk_usage(str(ROOT)).free / 1024 / 1024 / 1024,
                },
                "status": "healthy"
                if (
                    memory_info.rss / 1024 / 1024 < self.config["max_memory_mb"]
                    and cpu_percent < self.config["max_cpu_percent"]
                )
                else "warning",
            }
        except Exception as e:
            logger.error(f"❌ Error checking resources: {e}")
            return {"status": "error", "error": str(e)}

    def save_system_state(self, state: dict[str, Any]):
        """Save system state atomically."""
        if self.state_manager:
            try:
                self.state_manager.save_state(state)
            except Exception as e:
                logger.error(f"❌ Error saving state: {e}")
        else:
            try:
                SYSTEM_STATE_FILE.write_text(json.dumps(state, indent=2))
            except Exception as e:
                logger.error(f"❌ Error saving state: {e}")


@world_class_agent("foundation", state_file=SYSTEM_STATE_FILE, paper_mode_only=True)
def main():
    """Main foundation system loop."""
    logger.info("🚀 Foundation System starting...")

    manager = FoundationManager()

    # Validate dependencies
    deps = manager.validate_dependencies()
    missing = [k for k, v in deps.items() if not v]
    if missing:
        logger.warning(f"⚠️ Missing dependencies: {missing}")
    else:
        logger.info("✅ All dependencies available")

    # Initial system check
    resources = manager.check_system_resources()
    logger.info(
        f"📊 System Resources: {resources['memory_mb']:.1f}MB memory, {resources['cpu_percent']:.1f}% CPU"
    )

    # Save initial state
    initial_state = {
        "startup_time": datetime.now(UTC).isoformat(),
        "config": manager.config,
        "dependencies": deps,
        "resources": resources,
    }
    manager.save_system_state(initial_state)

    # Monitor loop
    check_interval = manager.config["health_check_interval"]
    while True:
        try:
            time.sleep(check_interval)

            # Periodic resource check
            resources = manager.check_system_resources()
            if resources["status"] == "warning":
                logger.warning(
                    f"⚠️ Resource warning: {resources['memory_mb']:.1f}MB memory, {resources['cpu_percent']:.1f}% CPU"
                )

            # Update state
            current_state = {
                "last_check": datetime.now(UTC).isoformat(),
                "resources": resources,
                "dependencies": manager.validate_dependencies(),
            }
            manager.save_system_state(current_state)

        except KeyboardInterrupt:
            logger.info("🛑 Foundation System stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in foundation loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
