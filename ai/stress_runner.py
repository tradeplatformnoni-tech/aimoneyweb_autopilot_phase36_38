"""
Scenario Stress Testing Runner
Runs hourly stress tests and pushes results to dashboard
World-class: Retry logic, error handling, graceful degradation
"""

import time
from datetime import datetime
from typing import Any

import requests

RISK_ENGINE_URL = "http://localhost:8300"
DASHBOARD_URL = "http://localhost:8100"
RETRY_DELAYS = [1, 2, 4]


def run_stress_test(
    positions: list[dict[str, Any]], scenarios: list[dict[str, Any]], max_retries: int = 3
) -> dict[str, Any]:
    """
    Run stress test on risk engine.

    Args:
        positions: List of position dicts with symbol, qty, price
        scenarios: List of scenario dicts with name and shocks
        max_retries: Maximum retry attempts

    Returns:
        Stress test results
    """
    url = f"{RISK_ENGINE_URL}/risk/stress"
    payload = {"positions": positions, "scenarios": scenarios}

    for attempt in range(max_retries):
        try:
            # Health check
            if attempt > 0:
                try:
                    health = requests.get(f"{RISK_ENGINE_URL}/health", timeout=2)
                    if health.status_code != 200:
                        time.sleep(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])
                        continue
                except:
                    time.sleep(RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)])
                    continue

            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                print(
                    f"[stress_runner] Stress test completed: {len(data.get('results', []))} scenarios",
                    flush=True,
                )
                return data
            else:
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                    continue
                else:
                    return {"error": f"HTTP {response.status_code}", "results": []}

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
            else:
                print(f"[stress_runner] Connection failed after {max_retries} attempts", flush=True)
                return {"error": "Connection failed", "results": []}
        except Exception as e:
            print(f"[stress_runner] Error: {e}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
            else:
                return {"error": str(e), "results": []}

    return {"error": "Max retries exceeded", "results": []}


def push_stress_results_to_dashboard(results: dict[str, Any]) -> bool:
    """Push stress test results to dashboard."""
    try:
        # Update meta metrics with stress results
        response = requests.post(
            f"{DASHBOARD_URL}/meta/metrics",
            json={"stress_last": results, "stress_timestamp": datetime.now().isoformat()},
            timeout=10,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[stress_runner] Failed to push to dashboard: {e}", flush=True)
        return False


def main():
    """Main stress test runner (hourly)."""
    print(f"[stress_runner] Starting stress test runner @ {datetime.now().isoformat()}", flush=True)

    # Example positions (would come from actual portfolio state)
    positions = [
        {"symbol": "BTC-USD", "quantity": 0.05, "price": 107000.0},
        {"symbol": "ETH-USD", "quantity": 1.0, "price": 3600.0},
    ]

    # Example scenarios
    scenarios = [
        {"name": "BTC -15% overnight", "shocks": {"BTC-USD": -0.15}},
        {"name": "ETH -20%", "shocks": {"ETH-USD": -0.20}},
        {"name": "Market crash -30%", "shocks": {"BTC-USD": -0.30, "ETH-USD": -0.30}},
    ]

    # Run stress test
    results = run_stress_test(positions, scenarios)

    # Push to dashboard
    if "error" not in results:
        push_stress_results_to_dashboard(results)
        print("[stress_runner] Stress test completed and pushed to dashboard", flush=True)
    else:
        print(f"[stress_runner] Stress test failed: {results.get('error', 'Unknown')}", flush=True)


if __name__ == "__main__":
    main()
