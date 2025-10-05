from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Dict, Iterable, List, Optional

import httpx

from .interfaces import PageFetcher, StorageAdapter
from .resilience import BulkheadExecutor, CircuitBreaker, CircuitBreakerOpen


USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/124.0",
]


class RequestsFetcher(PageFetcher):
    """HTTPX-based fetcher with circuit-breaker, bulkhead, and caching."""

    def __init__(
        self,
        *,
        timeout: float = 20.0,
        retries: int = 2,
        cache: Optional[StorageAdapter] = None,
        cache_ttl: int = 3600,
        circuit_breaker: Optional[CircuitBreaker] = None,
        bulkhead: Optional[BulkheadExecutor] = None,
        rate_limit_per_sec: Optional[int] = None,
    ) -> None:
        self._timeout = timeout
        self._retries = retries
        self._cache = cache
        self._cache_ttl = cache_ttl
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._bulkhead = bulkhead or BulkheadExecutor(max_concurrency=5)
        self._rate_limit_window = 1.0 / rate_limit_per_sec if rate_limit_per_sec else None
        self._last_request_ts = 0.0

    async def fetch(self, url: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cache_key = f"requests:{url}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                cached["source"] = "cache"
                return cached

        async def _call() -> Dict[str, Any]:
            if self._rate_limit_window:
                await self._respect_rate_limit()
            for attempt in range(self._retries + 1):
                headers = {"User-Agent": random.choice(USER_AGENT_POOL)}
                try:
                    async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                        response = await client.get(url, headers=headers)
                    payload = {
                        "url": url,
                        "status": response.status_code,
                        "headers": dict(response.headers),
                        "html": response.text,
                        "fetched_at": time.time(),
                        "source": "live",
                    }
                    if self._cache:
                        self._cache.put(cache_key, payload, ttl=self._cache_ttl)
                    return payload
                except httpx.RequestError as exc:
                    if attempt == self._retries:
                        raise
                    await asyncio.sleep(0.5 * (attempt + 1))
            raise RuntimeError("Unreachable fetch loop")

        try:
            result = await self._circuit_breaker.run(lambda: self._bulkhead.run(_call))
        except CircuitBreakerOpen:
            if self._cache:
                cached = self._cache.get(cache_key)
                if cached:
                    cached["source"] = "stale"
                    return cached
            raise
        return result

    async def _respect_rate_limit(self) -> None:
        now = time.time()
        wait = self._rate_limit_window - (now - self._last_request_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request_ts = time.time()


class PlaywrightFetcher(PageFetcher):
    """Async Playwright wrapper with graceful degradation."""

    def __init__(self, *, timeout_ms: int = 30000, wait_for_selector: Optional[str] = None) -> None:
        self._timeout_ms = timeout_ms
        self._wait_for_selector = wait_for_selector

    async def fetch(self, url: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            return {
                "url": url,
                "status": None,
                "headers": {},
                "html": "",
                "error": f"playwright unavailable: {exc}",
                "source": "playwright-unavailable",
            }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=self._timeout_ms)
            if self._wait_for_selector:
                await page.wait_for_selector(self._wait_for_selector, timeout=self._timeout_ms)
            html = await page.content()
            status = response.status if response else None
            await browser.close()
        return {
            "url": url,
            "status": status,
            "headers": {},
            "html": html,
            "source": "playwright",
        }


class FallbackPageFetcher(PageFetcher):
    """Chains multiple fetchers until one succeeds."""

    def __init__(self, fetchers: Iterable[PageFetcher]) -> None:
        self._fetchers = list(fetchers)

    async def fetch(self, url: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        for fetcher in self._fetchers:
            try:
                result = await fetcher.fetch(url, context=context)
                if result.get("html"):
                    return result
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise RuntimeError("No fetchers configured")


__all__ = ["FallbackPageFetcher", "PlaywrightFetcher", "RequestsFetcher"]
