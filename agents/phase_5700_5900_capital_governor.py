#!/usr/bin/env python3
"""
Phase 5700-5900: Capital Governor Intelligence
Dynamically reallocates capital between agents based on meta-metrics
Uses PnL, Sharpe, win rate, and drawdown to optimize capital allocation
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
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

DASHBOARD_URL = os.getenv("NEOLIGHT_DASHBOARD_URL", "http://localhost:8100")
UPDATE_INTERVAL = int(os.getenv("CAPITAL_GOVERNOR_INTERVAL", "300"))  # 5 minutes
MIN_ALLOCATION = float(os.getenv("CAPITAL_GOVERNOR_MIN_ALLOC", "0.05"))  # 5% minimum
MAX_ALLOCATION = float(os.getenv("CAPITAL_GOVERNOR_MAX_ALLOC", "0.40"))  # 40% maximum
REALLOCATION_THRESHOLD = float(
    os.getenv("CAPITAL_GOVERNOR_THRESHOLD", "0.10")
)  # 10% change triggers reallocation

# Output file for capital allocations
CAPITAL_ALLOCATIONS_FILE = RUNTIME / "capital_governor_allocations.json"
ALLOCATIONS_OVERRIDE_FILE = RUNTIME / "allocations_override.json"


def fetch_meta_metrics(max_retries: int = 3, retry_delay: int = 10) -> dict[str, Any] | None:
    """
    Fetch meta-metrics from dashboard with retry logic and health check.
    World-class: Graceful degradation, exponential backoff, health monitoring.
    On Render, return None (no localhost dashboard available).
    """
    if not DASHBOARD_URL:
        # On Render, skip dashboard fetch (no localhost available)
        return None
    for attempt in range(max_retries):
        try:
            # Health check first
            health_response = requests.get(f"{DASHBOARD_URL}/status", timeout=3)
            if health_response.status_code != 200:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)  # Exponential backoff
                    print(
                        f"[capital_governor] Dashboard health check failed (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                        flush=True,
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    print(
                        f"[capital_governor] Dashboard unhealthy after {max_retries} attempts",
                        flush=True,
                    )
                    return None

            # Fetch metrics
            response = requests.get(f"{DASHBOARD_URL}/meta/metrics", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Validate response structure
                if isinstance(data, dict) and ("per_agent" in data or "timestamp" in data):
                    print(
                        f"[capital_governor] Meta-metrics fetched successfully (attempt {attempt + 1})",
                        flush=True,
                    )
                    return data
                else:
                    print("[capital_governor] Invalid metrics structure received", flush=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
            else:
                print(
                    f"[capital_governor] HTTP {response.status_code} from dashboard (attempt {attempt + 1}/{max_retries})",
                    flush=True,
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2**attempt))
                    continue
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)
                print(
                    f"[capital_governor] Connection refused - dashboard not ready (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                    flush=True,
                )
                time.sleep(wait_time)
            else:
                print(
                    f"[capital_governor] Dashboard connection failed after {max_retries} attempts: {e}",
                    flush=True,
                )
        except Exception as e:
            print(f"[capital_governor] Error fetching meta-metrics: {e}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                traceback.print_exc()

    return None


def calculate_agent_score(agent_metrics: dict[str, Any]) -> float:
    """
    Calculate composite score for agent based on multiple factors.
    Higher score = better performance = more capital allocation.

    Factors:
    - PnL 7d (40% weight)
    - Sharpe 30d (30% weight)
    - Win rate 30d (20% weight)
    - Max drawdown penalty (10% weight)
    """
    pnl_7d = agent_metrics.get("pnl_7d", 0.0)
    sharpe_30d = agent_metrics.get("sharpe_30d", 0.0)
    winrate_30d = agent_metrics.get("winrate_30d", 0.0)
    max_dd_30d = agent_metrics.get("max_dd_30d", 0.0)

    # Normalize PnL (assume max $10k for 7d, scale to 0-1)
    pnl_normalized = max(0.0, min(1.0, pnl_7d / 10000.0))

    # Normalize Sharpe (assume max 3.0, scale to 0-1)
    sharpe_normalized = max(0.0, min(1.0, sharpe_30d / 3.0))

    # Win rate is already 0-1
    winrate_normalized = winrate_30d

    # Drawdown penalty (inverse: higher drawdown = lower score)
    # Max DD of 20% = 0 score, 0% DD = 1.0 score
    dd_penalty = max(0.0, 1.0 - (max_dd_30d / 20.0))

    # Composite score
    score = (
        pnl_normalized * 0.40
        + sharpe_normalized * 0.30
        + winrate_normalized * 0.20
        + dd_penalty * 0.10
    )

    return round(score, 4)


def calculate_strategy_score(strategy_metrics: dict[str, Any]) -> float:
    """Calculate score for strategy (similar to agent score)."""
    sharpe_30d = strategy_metrics.get("sharpe_30d", 0.0)
    score = strategy_metrics.get("score", 0.0)
    max_dd_30d = strategy_metrics.get("max_dd_30d", 0.0)

    # Use strategy score if available, otherwise calculate from Sharpe
    if score > 0:
        base_score = score
    else:
        base_score = max(0.0, min(1.0, sharpe_30d / 3.0))

    # Apply drawdown penalty
    dd_penalty = max(0.0, 1.0 - (max_dd_30d / 20.0))

    final_score = base_score * 0.8 + dd_penalty * 0.2
    return round(final_score, 4)


def normalize_allocations(allocations: dict[str, float]) -> dict[str, float]:
    """Normalize allocations to sum to 1.0, apply min/max constraints."""
    # Filter out negative values
    filtered = {k: max(0.0, v) for k, v in allocations.items()}

    # Apply min/max constraints
    constrained = {}
    for agent, alloc in filtered.items():
        constrained[agent] = max(MIN_ALLOCATION, min(MAX_ALLOCATION, alloc))

    # Normalize to sum to 1.0
    total = sum(constrained.values())
    if total <= 0:
        # Default equal allocation if no valid scores
        num_agents = len(constrained)
        if num_agents > 0:
            return dict.fromkeys(constrained.keys(), 1.0 / num_agents)
        return {}

    normalized = {agent: alloc / total for agent, alloc in constrained.items()}

    # Round to 4 decimal places
    return {agent: round(alloc, 4) for agent, alloc in normalized.items()}


def calculate_agent_allocations(meta_metrics: dict[str, Any]) -> dict[str, float]:
    """
    Calculate optimal capital allocation across agents.
    Returns: {agent_name: allocation_percentage}
    """
    per_agent = meta_metrics.get("per_agent", {})
    guardian = meta_metrics.get("guardian", {})
    market_regime = meta_metrics.get("market_regime", {})

    # Check if Guardian is paused
    if guardian.get("is_paused", False):
        print("[capital_governor] Guardian paused - maintaining current allocations", flush=True)
        return load_current_allocations()

    # Get regime risk multiplier
    risk_multiplier = market_regime.get("risk_multiplier", 1.0)

    # Calculate scores for each agent
    agent_scores = {}
    for agent_name, agent_metrics in per_agent.items():
        score = calculate_agent_score(agent_metrics)
        agent_scores[agent_name] = score
        print(
            f"[capital_governor] {agent_name}: score={score:.4f} (PnL={agent_metrics.get('pnl_7d', 0):.2f}, Sharpe={agent_metrics.get('sharpe_30d', 0):.3f}, WR={agent_metrics.get('winrate_30d', 0):.3f})",
            flush=True,
        )

    if not agent_scores:
        print(
            "[capital_governor] No agent metrics available - using default allocation", flush=True
        )
        return {}

    # Convert scores to allocations (proportional to scores)
    allocations = agent_scores.copy()

    # Apply regime risk multiplier (reduce allocation in high-risk regimes)
    if risk_multiplier < 1.0:
        allocations = {agent: alloc * risk_multiplier for agent, alloc in allocations.items()}
        print(f"[capital_governor] Applied risk multiplier: {risk_multiplier:.2f}", flush=True)

    # Normalize allocations
    normalized = normalize_allocations(allocations)

    return normalized


def calculate_strategy_allocations(meta_metrics: dict[str, Any]) -> dict[str, float]:
    """
    Calculate optimal allocation across strategies.
    Returns: {strategy_name: allocation_percentage}
    """
    per_strategy = meta_metrics.get("per_strategy", {})

    if not per_strategy:
        return {}

    # Calculate scores for each strategy
    strategy_scores = {}
    for strategy_name, strategy_metrics in per_strategy.items():
        score = calculate_strategy_score(strategy_metrics)
        strategy_scores[strategy_name] = score

    # Normalize allocations
    normalized = normalize_allocations(strategy_scores)

    return normalized


def load_current_allocations() -> dict[str, float]:
    """Load current capital allocations."""
    if CAPITAL_ALLOCATIONS_FILE.exists():
        try:
            data = json.loads(CAPITAL_ALLOCATIONS_FILE.read_text())
            return data.get("allocations", {})
        except:
            pass

    # Fallback to allocations_override.json
    if ALLOCATIONS_OVERRIDE_FILE.exists():
        try:
            data = json.loads(ALLOCATIONS_OVERRIDE_FILE.read_text())
            return data.get("allocations", {})
        except:
            pass

    return {}


def save_allocations(allocations: dict[str, float], source: str = "capital_governor") -> None:
    """Save capital allocations to file."""
    try:
        data = {
            "allocations": allocations,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
            "min_allocation": MIN_ALLOCATION,
            "max_allocation": MAX_ALLOCATION,
        }
        CAPITAL_ALLOCATIONS_FILE.write_text(json.dumps(data, indent=2))

        # Also update allocations_override.json for SmartTrader compatibility
        override_data = {
            "allocations": allocations,
            "source": source,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        ALLOCATIONS_OVERRIDE_FILE.write_text(json.dumps(override_data, indent=2))

        print(f"[capital_governor] Allocations saved: {allocations}", flush=True)
    except Exception as e:
        print(f"[capital_governor] Failed to save allocations: {e}", flush=True)
        traceback.print_exc()


def should_reallocate(
    new_allocations: dict[str, float], current_allocations: dict[str, float]
) -> bool:
    """Check if reallocation is needed (change > threshold)."""
    if not current_allocations:
        return True  # First allocation

    # Calculate maximum change in any allocation
    max_change = 0.0
    for agent in set(list(new_allocations.keys()) + list(current_allocations.keys())):
        new_alloc = new_allocations.get(agent, 0.0)
        current_alloc = current_allocations.get(agent, 0.0)
        change = abs(new_alloc - current_alloc)
        max_change = max(max_change, change)

    return max_change >= REALLOCATION_THRESHOLD


def send_telegram(message: str) -> None:
    """Send Telegram notification."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=5,
            )
    except:
        pass  # Silent fail


def wait_for_dashboard(max_wait: int = 300) -> bool:
    """
    Wait for dashboard to become available.
    World-class: Health check with timeout, graceful startup.
    On Render, skip wait (no localhost dashboard available).
    """
    if not DASHBOARD_URL:
        # On Render, skip dashboard wait (no localhost available)
        print("[capital_governor] Running on Render - skipping dashboard wait", flush=True)
        return True
    print(
        f"[capital_governor] Waiting for dashboard to become available (max {max_wait}s)...",
        flush=True,
    )
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{DASHBOARD_URL}/status", timeout=3)
            if response.status_code == 200:
                print("[capital_governor] ✅ Dashboard is available!", flush=True)
                return True
        except:
            pass
        time.sleep(5)
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0:  # Print every 30 seconds
            print(
                f"[capital_governor] Still waiting for dashboard... ({elapsed}/{max_wait}s)",
                flush=True,
            )

    print(
        f"[capital_governor] ⚠️ Dashboard not available after {max_wait}s - continuing with retry logic",
        flush=True,
    )
    return False


def main() -> None:
    """Main Capital Governor loop with world-class enhancements."""
    print(
        f"[capital_governor] 🚀 Starting Capital Governor Intelligence @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )
    print(
        f"[capital_governor] Config: min_alloc={MIN_ALLOCATION}, max_alloc={MAX_ALLOCATION}, threshold={REALLOCATION_THRESHOLD}",
        flush=True,
    )
    print(f"[capital_governor] Dashboard URL: {DASHBOARD_URL}", flush=True)

    # Wait for dashboard on startup
    wait_for_dashboard(max_wait=300)

    current_allocations = load_current_allocations()
    consecutive_failures = 0
    max_consecutive_failures = 10

    while True:
        try:
            # Fetch meta-metrics with retry logic
            meta_metrics = fetch_meta_metrics(max_retries=3, retry_delay=10)
            if not meta_metrics:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(
                        f"[capital_governor] ⚠️ Too many consecutive failures ({consecutive_failures}) - entering degraded mode",
                        flush=True,
                    )
                    # In degraded mode, maintain current allocations
                    time.sleep(UPDATE_INTERVAL * 2)  # Check less frequently
                    continue
                print(
                    f"[capital_governor] No meta-metrics available - waiting... (failure {consecutive_failures}/{max_consecutive_failures})",
                    flush=True,
                )
                time.sleep(UPDATE_INTERVAL)
                continue

            consecutive_failures = 0  # Reset on success

            # Calculate new allocations
            new_allocations = calculate_agent_allocations(meta_metrics)

            if not new_allocations:
                print("[capital_governor] No allocations calculated - skipping", flush=True)
                time.sleep(UPDATE_INTERVAL)
                continue

            # Check if reallocation is needed
            if should_reallocate(new_allocations, current_allocations):
                print(
                    f"[capital_governor] Reallocation triggered (change >= {REALLOCATION_THRESHOLD})",
                    flush=True,
                )
                print(f"[capital_governor] Old: {current_allocations}", flush=True)
                print(f"[capital_governor] New: {new_allocations}", flush=True)

                # Save new allocations
                save_allocations(new_allocations)

                # Send Telegram notification
                msg = "🎯 Capital Reallocation:\n"
                for agent, alloc in sorted(
                    new_allocations.items(), key=lambda x: x[1], reverse=True
                ):
                    msg += f"{agent}: {alloc * 100:.1f}%\n"
                send_telegram(msg)

                current_allocations = new_allocations
            else:
                print(
                    f"[capital_governor] No reallocation needed (max change < {REALLOCATION_THRESHOLD})",
                    flush=True,
                )

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("[capital_governor] 🛑 Shutting down gracefully...", flush=True)
            break
        except Exception as e:
            consecutive_failures += 1
            print(f"[capital_governor] ❌ Loop error: {e}", flush=True)
            traceback.print_exc()
            if consecutive_failures >= max_consecutive_failures:
                print(
                    f"[capital_governor] ⚠️ Entering degraded mode after {consecutive_failures} errors",
                    flush=True,
                )
                time.sleep(UPDATE_INTERVAL * 2)
            else:
                time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
