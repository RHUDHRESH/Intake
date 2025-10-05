"""LangChain tool for crawling web pages via modular fetchers."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field, HttpUrl

from Intake.market_research import ConfigManager
from Intake.market_research.fetchers import FallbackPageFetcher, PlaywrightFetcher, RequestsFetcher
from Intake.market_research.parsers import SoupHTMLParser
from Intake.market_research.storage import InMemoryStorageAdapter, JSONFileStorageAdapter
from Intake.market_research.telemetry import emit_log


class WebCrawlerInput(BaseModel):
    url: HttpUrl = Field(..., description="Fully qualified URL to crawl")
    site_key: str = Field("default", description="Site config to apply from config file")
    timeout_ms: int = Field(30000, ge=1000, le=120000)
    wait_for_selector: Optional[str] = Field(
        None,
        description="Optional CSS selector to await before extracting content",
    )
    text_limit: int = Field(5000, ge=500, le=50000)


class WebCrawlerTool(BaseTool):
    name: str = "web_crawler_tool"
    description: str = (
        "Fetches a web page using resilient fetchers, returning title, html, "
        "and extracted text."
    )
    args_schema: type = WebCrawlerInput

    def __init__(
        self,
        *,
        config_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        super().__init__()
        self._config_manager = ConfigManager(config_path) if config_path else None
        cache_dir = cache_dir or Path("data/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = JSONFileStorageAdapter(cache_dir)
        self._memory_cache = InMemoryStorageAdapter()
        self._parser = SoupHTMLParser()

    def _run(
        self,
        url: str,
        site_key: str = "default",
        timeout_ms: int = 30000,
        wait_for_selector: Optional[str] = None,
        text_limit: int = 5000,
    ) -> Dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task instead
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._arun(
                        url=url,
                        site_key=site_key,
                        timeout_ms=timeout_ms,
                        wait_for_selector=wait_for_selector,
                        text_limit=text_limit,
                    )
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to call asyncio.run
            return asyncio.run(
                self._arun(
                    url=url,
                    site_key=site_key,
                    timeout_ms=timeout_ms,
                    wait_for_selector=wait_for_selector,
                    text_limit=text_limit,
                )
            )

    async def _arun(
        self,
        url: str,
        site_key: str = "default",
        timeout_ms: int = 30000,
        wait_for_selector: Optional[str] = None,
        text_limit: int = 5000,
    ) -> Dict[str, Any]:
        site_config = self._load_site_config(site_key)
        cache_key = f"tool:{url}"
        cached = self._cache.get(cache_key)
        if cached:
            cached["source"] = "file-cache"
            emit_log("web_crawler.cache.hit", extra={"url": url, "site_key": site_key})
            return cached
        fetcher = self._build_fetcher(site_config, wait_for_selector=wait_for_selector)
        result = await fetcher.fetch(url, context={"site": site_key, "timeout": timeout_ms / 1000})
        parsed = self._parser.parse(result.get("html", ""), url=url)
        text = parsed.get("text", "")
        if len(text) > text_limit:
            text = text[:text_limit]
        payload = {
            "url": url,
            "site_key": site_key,
            "status": result.get("status"),
            "source": result.get("source"),
            "title": parsed.get("title"),
            "html": result.get("html"),
            "text": text,
            "metadata": {"wait_for_selector": wait_for_selector, **site_config},
        }
        self._cache.put(cache_key, payload, ttl=site_config.get("cache_ttl", 3600))
        emit_log("web_crawler.fetch.success", extra={"url": url, "site_key": site_key})
        return payload

    def _load_site_config(self, site_key: str) -> Dict[str, Any]:
        if not self._config_manager:
            return {}
        return self._config_manager.get_site(site_key)

    def _build_fetcher(
        self,
        site_config: Dict[str, Any],
        *,
        wait_for_selector: Optional[str],
    ) -> FallbackPageFetcher:
        rate_limit = site_config.get("rate_limit") or 5
        return FallbackPageFetcher(
            [
                PlaywrightFetcher(wait_for_selector=wait_for_selector),
                RequestsFetcher(cache=self._memory_cache, rate_limit_per_sec=rate_limit),
            ]
        )


__all__ = ["WebCrawlerTool"]
