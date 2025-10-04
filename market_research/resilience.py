from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Coroutine, Optional


class CircuitBreakerOpen(Exception):
    """Raised when a circuit breaker refuses a call."""


class CircuitBreaker:
    """Simple circuit breaker for guarding flaky external integrations."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = "closed"
        self._opened_at: Optional[float] = None

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._state = "open"
            self._opened_at = time.time()

    def allow(self) -> bool:
        if self._state == "closed":
            return True
        assert self._opened_at is not None
        if time.time() - self._opened_at >= self._recovery_timeout:
            self._state = "half_open"
            return True
        return False

    async def run(self, coro_factory: Callable[[], Awaitable[Any]]) -> Any:
        if not self.allow():
            raise CircuitBreakerOpen("Circuit breaker is open")
        try:
            result = await coro_factory()
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()
            return result


class BulkheadExecutor:
    """Concurrency guard that limits simultaneous coroutine execution."""

    def __init__(self, *, max_concurrency: int) -> None:
        self._sem = asyncio.Semaphore(max_concurrency)

    async def run(self, coro_factory: Callable[[], Awaitable[Any]]) -> Any:
        async with self._sem:
            return await coro_factory()

    @asynccontextmanager
    async def slot(self) -> Coroutine[Any, Any, None]:
        async with self._sem:
            yield


__all__ = ["CircuitBreaker", "CircuitBreakerOpen", "BulkheadExecutor"]
