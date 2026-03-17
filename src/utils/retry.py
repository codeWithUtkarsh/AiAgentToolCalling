"""
Retry Utilities with Exponential Backoff

Provides retry logic for API calls and external operations that may
transiently fail (rate limits, network timeouts, etc.).

Inspired by production patterns for handling Anthropic API rate limits
when processing repositories with 50+ dependencies.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Sequence, Type, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Sequence[Type[Exception]] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay cap in seconds
        backoff_factor: Multiplier for delay after each retry
        retryable_exceptions: Tuple of exception types that trigger a retry

    Example:
        @retry_with_backoff(max_retries=3, retryable_exceptions=(anthropic.RateLimitError,))
        def call_api():
            return client.messages.create(...)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            delay = base_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(retryable_exceptions) as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore[return-value]

    return decorator
