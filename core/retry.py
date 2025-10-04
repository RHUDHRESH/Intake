"""Retry utilities with exponential backoff."""
from __future__ import annotations

import asyncio
import functools
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Tuple, Type

from .errors import AgentError, RetryableAgentError, ValidationError


@dataclass
class RetryPolicy:
    attempts: int = 3
    base_delay: float = 0.5
    backoff_factor: float = 2.0
    max_delay: float = 30.0
    jitter: Tuple[float, float] = (0.0, 0.0)
    retry_exceptions: Tuple[Type[Exception], ...] = (RetryableAgentError,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (ValidationError,)


def _should_retry(error: Exception, policy: RetryPolicy) -> bool:
    if isinstance(error, policy.non_retryable_exceptions):
        return False
    if not policy.retry_exceptions:
        return isinstance(error, AgentError) and getattr(error, "retryable", False)
    return isinstance(error, policy.retry_exceptions)


def _compute_delay(attempt: int, policy: RetryPolicy) -> float:
    delay = policy.base_delay * (policy.backoff_factor ** (attempt - 1))
    delay = min(delay, policy.max_delay)
    if policy.jitter != (0.0, 0.0):
        lo, hi = policy.jitter
        delay += random.uniform(lo, hi)
    return delay


async def retry_async(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    policy: Optional[RetryPolicy] = None,
    **kwargs: Any,
) -> Any:
    policy = policy or RetryPolicy()
    last_error: Optional[Exception] = None

    for attempt in range(1, policy.attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == policy.attempts or not _should_retry(exc, policy):
                raise
            await asyncio.sleep(_compute_delay(attempt, policy))

    if last_error:
        raise last_error
    raise RuntimeError("retry_async exited without executing the function")


def retry_sync(
    func: Callable[..., Any],
    *args: Any,
    policy: Optional[RetryPolicy] = None,
    **kwargs: Any,
) -> Any:
    policy = policy or RetryPolicy()
    last_error: Optional[Exception] = None

    for attempt in range(1, policy.attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == policy.attempts or not _should_retry(exc, policy):
                raise
            delay = _compute_delay(attempt, policy)
            time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError("retry_sync exited without executing the function")


def with_retry(
    policy: Optional[RetryPolicy] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator applying retry logic to sync or async callables."""

    policy = policy or RetryPolicy()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await retry_async(func, *args, policy=policy, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return retry_sync(func, *args, policy=policy, **kwargs)

        return sync_wrapper

    return decorator
