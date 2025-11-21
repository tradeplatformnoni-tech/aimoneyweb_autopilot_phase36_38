#!/usr/bin/env python3
"""
World-Class Agent Wrapper
--------------------------
Universal wrapper that applies all world-class utilities to any agent.
Ensures paper-mode compatibility and Einstein-level stability.
"""

import os
import sys
import traceback
from collections.abc import Callable
from functools import wraps
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))

# Import world-class utilities
try:
    from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
    from utils.health_check import HealthCheck, HealthStatus
    from utils.retry import retry_on_network_error, retry_with_backoff
    from utils.state_manager import StateManager
    from utils.structured_logging import setup_structured_logging

    HAS_UTILS = True
except ImportError as e:
    HAS_UTILS = False
    print(f"⚠️ World-class utilities not available: {e}")


def world_class_agent(
    agent_name: str,
    state_file: Path | None = None,
    health_check_interval: float = 60.0,
    paper_mode_only: bool = True,
):
    """
    World-class agent decorator that applies all stability improvements.

    Args:
        agent_name: Name of the agent
        state_file: Optional state file path
        health_check_interval: Health check interval in seconds
        paper_mode_only: If True, only runs in paper mode (default: True)

    Usage:
        @world_class_agent("my_agent", state_file=Path("state/my_agent.json"))
        def main():
            # Agent code here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check paper mode if required
            if paper_mode_only:
                trading_mode = os.getenv("NEOLIGHT_TRADING_MODE", "PAPER_TRADING_MODE")
                if trading_mode == "LIVE_MODE":
                    print(f"⚠️ {agent_name}: Skipping in LIVE_MODE (paper-mode only agent)")
                    return

            # Initialize state manager
            state_manager = None
            if HAS_UTILS and state_file:
                try:
                    state_manager = StateManager(
                        state_file, default_state={}, backup_count=24, backup_interval=3600.0
                    )
                except Exception as e:
                    print(f"⚠️ {agent_name}: StateManager init failed: {e}")

            # Initialize health check
            health_check = None
            if HAS_UTILS:
                try:
                    health_check = HealthCheck(agent_name, check_interval=health_check_interval)

                    # Add default health checks
                    if state_file:

                        def check_state():
                            from utils.health_check import check_file_exists

                            return check_file_exists(str(state_file), max_age=3600)

                        health_check.add_check(check_state, "state_file")

                    health_check.start_monitoring()
                except Exception as e:
                    print(f"⚠️ {agent_name}: HealthCheck init failed: {e}")

            # Initialize circuit breaker for external calls
            circuit_breaker = None
            if HAS_UTILS:
                try:
                    circuit_breaker = CircuitBreaker(
                        f"{agent_name}_external", failure_threshold=5, timeout=60.0
                    )
                except Exception as e:
                    print(f"⚠️ {agent_name}: CircuitBreaker init failed: {e}")

            # Setup structured logging
            logger = None
            if HAS_UTILS:
                try:
                    log_file = ROOT / "logs" / f"{agent_name}.log"
                    logger = setup_structured_logging(
                        agent_name,
                        log_file=log_file,
                        level=20,  # INFO
                        console=True,
                    )
                except Exception as e:
                    print(f"⚠️ {agent_name}: Structured logging init failed: {e}")

            # Run agent with error handling
            try:
                print(f"🚀 {agent_name}: Starting with world-class stability...")
                result = func(*args, **kwargs)
                print(f"✅ {agent_name}: Completed successfully")
                return result
            except KeyboardInterrupt:
                print(f"🛑 {agent_name}: Stopped by user")
                if health_check:
                    health_check.stop_monitoring()
                raise
            except Exception as e:
                print(f"❌ {agent_name}: Error: {e}")
                if logger:
                    logger.error(f"Agent error: {e}", exc_info=True)
                traceback.print_exc()
                raise
            finally:
                if health_check:
                    health_check.stop_monitoring()

        return wrapper

    return decorator


def apply_to_agent_file(agent_file: Path):
    """
    Apply world-class utilities to an agent file.
    Adds imports and wraps main() function.
    """
    if not agent_file.exists():
        return False

    content = agent_file.read_text()

    # Check if already has world-class utilities
    if "world_class_agent" in content or "from utils" in content:
        return False  # Already applied

    # Add imports at top (after existing imports)
    imports = """
# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    from utils.circuit_breaker import CircuitBreaker
    from utils.retry import retry_with_backoff
    from utils.health_check import HealthCheck
    from utils.state_manager import StateManager
    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False
"""

    # Find main function and wrap it
    if "def main()" in content:
        # Add imports
        lines = content.split("\n")
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                import_end = i + 1

        lines.insert(import_end, imports)

        # Wrap main function
        content = "\n".join(lines)
        content = content.replace(
            "def main():",
            '@world_class_agent("' + agent_file.stem + '", paper_mode_only=True)\ndef main():',
        )

        agent_file.write_text(content)
        return True

    return False
