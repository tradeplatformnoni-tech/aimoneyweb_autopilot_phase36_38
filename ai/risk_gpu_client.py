"""
GPU Risk Engine Client for Python
World-class: Retry logic with exponential backoff, health checks, graceful degradation
"""

import time
from typing import Any

import requests

RISK_GPU_URL = "http://localhost:8301"
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = [1, 2, 4]  # seconds


def compute_monte_carlo_var(
    returns: list[float],
    iterations: int = 200000,
    confidence: float = 0.99,
    seed: int | None = None,
    max_retries: int = DEFAULT_RETRIES,
) -> dict[str, Any]:
    """
    Compute Monte Carlo VaR using GPU risk engine.

    Args:
        returns: Historical daily returns
        iterations: Number of Monte Carlo iterations
        confidence: Confidence level (0.95, 0.99, etc.)
        seed: Optional random seed for reproducibility
        max_retries: Maximum retry attempts

    Returns:
        Dict with var, cvar, runtime_ms, iterations, confidence
    """
    url = f"{RISK_GPU_URL}/risk/mc_var"

    payload = {
        "returns": returns,
        "iterations": iterations,
        "confidence": confidence,
    }
    if seed is not None:
        payload["seed"] = seed

    for attempt in range(max_retries):
        try:
            # Health check first (quick)
            if attempt > 0:
                try:
                    health = requests.get(f"{RISK_GPU_URL}/health", timeout=2)
                    if health.status_code != 200:
                        wait_time = DEFAULT_BACKOFF[min(attempt - 1, len(DEFAULT_BACKOFF) - 1)]
                        print(
                            f"[risk_gpu] Health check failed (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                            flush=True,
                        )
                        time.sleep(wait_time)
                        continue
                except:
                    wait_time = DEFAULT_BACKOFF[min(attempt - 1, len(DEFAULT_BACKOFF) - 1)]
                    time.sleep(wait_time)
                    continue

            # Compute MC VaR
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                print(
                    f"[risk_gpu] MC VaR computed: var={data.get('var', 0):.2f}, cvar={data.get('cvar', 0):.2f}, runtime={data.get('runtime_ms', 0):.1f}ms",
                    flush=True,
                )
                return data
            else:
                if attempt < max_retries - 1:
                    wait_time = DEFAULT_BACKOFF[min(attempt, len(DEFAULT_BACKOFF) - 1)]
                    print(
                        f"[risk_gpu] HTTP {response.status_code} (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                        flush=True,
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    return {"error": f"HTTP {response.status_code}", "var": 0.0, "cvar": 0.0}

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                wait_time = DEFAULT_BACKOFF[min(attempt, len(DEFAULT_BACKOFF) - 1)]
                print(
                    f"[risk_gpu] Connection refused - service not ready (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                    flush=True,
                )
                time.sleep(wait_time)
            else:
                print(f"[risk_gpu] Connection failed after {max_retries} attempts", flush=True)
                return {"error": "Connection failed", "var": 0.0, "cvar": 0.0}
        except Exception as e:
            print(f"[risk_gpu] Error computing MC VaR: {e}", flush=True)
            if attempt < max_retries - 1:
                time.sleep(DEFAULT_BACKOFF[min(attempt, len(DEFAULT_BACKOFF) - 1)])
            else:
                return {"error": str(e), "var": 0.0, "cvar": 0.0}

    return {"error": "Max retries exceeded", "var": 0.0, "cvar": 0.0}


if __name__ == "__main__":
    # Test
    test_returns = [0.01, -0.02, 0.005, -0.003, 0.015, -0.01, 0.008]
    result = compute_monte_carlo_var(test_returns, iterations=200000, confidence=0.99)
    print(f"Result: {result}")
