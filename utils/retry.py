#!/usr/bin/env python3
"""
World-Class Retry Logic with Exponential Backoff
-------------------------------------------------
Standardized retry mechanism with exponential backoff, jitter, and configurable strategies.
"""

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class RetryStrategy:
    """Retry strategy configuration."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    CUSTOM = "custom"


def retry_with_backoff(
    func: Callable | None = None,
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    jitter_range: tuple[float, float] = (0.0, 0.3),
    strategy: str = RetryStrategy.EXPONENTIAL,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    retry_on_condition: Callable[[Exception], bool] | None = None,
    on_retry: Callable[[int, Exception], None] | None = None,
    on_failure: Callable[[Exception], None] | None = None,
):
    """
    World-class retry decorator with exponential backoff and jitter.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        jitter_range: Jitter range as (min, max) percentage
        strategy: Retry strategy (exponential, linear, fixed)
        retry_on: Exception types to retry on
        retry_on_condition: Custom condition function for retry
        on_retry: Callback on each retry (attempt_num, exception)
        on_failure: Callback on final failure (exception)

    Example:
        @retry_with_backoff(max_retries=5, base_delay=1.0)
        def fetch_data():
            return requests.get(url)
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # Check custom condition
                    if retry_on_condition and not retry_on_condition(e):
                        logger.debug(f"Retry condition not met for {f.__name__}: {e}")
                        raise

                    # Check if this is the last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"❌ {f.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        if on_failure:
                            on_failure(e)
                        raise

                    # Calculate delay
                    delay = _calculate_delay(
                        attempt=attempt,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        strategy=strategy,
                        jitter=jitter,
                        jitter_range=jitter_range,
                    )

                    # Call retry callback
                    if on_retry:
                        on_retry(attempt + 1, e)

                    logger.warning(
                        f"⚠️ {f.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)
                except Exception as e:
                    # Not in retry_on list, raise immediately
                    if not isinstance(e, retry_on):
                        raise
                    last_exception = e

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    # Support both @retry_with_backoff and @retry_with_backoff(...)
    if func is None:
        return decorator
    else:
        return decorator(func)


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    strategy: str,
    jitter: bool,
    jitter_range: tuple[float, float],
) -> float:
    """Calculate delay based on strategy."""
    if strategy == RetryStrategy.EXPONENTIAL:
        delay = base_delay * (exponential_base**attempt)
    elif strategy == RetryStrategy.LINEAR:
        delay = base_delay * (attempt + 1)
    elif strategy == RetryStrategy.FIXED:
        delay = base_delay
    else:
        delay = base_delay * (exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter
    if jitter:
        jitter_min, jitter_max = jitter_range
        jitter_amount = random.uniform(jitter_min, jitter_max) * delay
        delay = delay + jitter_amount

    return delay


def retry_on_network_error(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Specialized retry decorator for network operations.

    Retries on: ConnectionError, TimeoutError, requests.RequestException
    """
    import requests

    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=(
            ConnectionError,
            TimeoutError,
            requests.RequestException,
            requests.ConnectionError,
            requests.Timeout,
        ),
        on_retry=lambda attempt, e: logger.warning(f"🌐 Network error (attempt {attempt}): {e}"),
    )


def retry_on_api_error(max_retries: int = 3, base_delay: float = 2.0, max_delay: float = 60.0):
    """
    Specialized retry decorator for API calls.

    Retries on: HTTP 5xx errors, rate limit errors (429)
    """
    import requests

    def should_retry(e: Exception) -> bool:
        if isinstance(e, requests.HTTPError):
            status_code = getattr(e.response, "status_code", None)
            # Retry on 5xx errors and 429 (rate limit)
            return status_code and (status_code >= 500 or status_code == 429)
        return True

    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=(requests.RequestException,),
        retry_on_condition=should_retry,
        on_retry=lambda attempt, e: logger.warning(f"🔌 API error (attempt {attempt}): {e}"),
    )
