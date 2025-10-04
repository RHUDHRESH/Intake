from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph

from ..interfaces import HTMLParser, PageFetcher, StorageAdapter
from ..telemetry import PIPELINE_GAUGE, REQUEST_COUNTER, REQUEST_FAILURE, REQUEST_LATENCY, emit_log, traced_span


class DiscoveryState(TypedDict, total=False):
    seed_urls: List[str]
    discovered: List[Dict[str, Any]]
    raw_documents: List[Dict[str, Any]]
    config: Dict[str, Any]


def build_discovery_graph(
    *,
    fetcher: PageFetcher,
    parser: HTMLParser,
    cache: Optional[StorageAdapter] = None,
) -> StateGraph:
    graph = StateGraph(DiscoveryState)

    async def fetch_node(state: DiscoveryState) -> DiscoveryState:
        urls = state.get("seed_urls", [])
        config = state.get("config", {})
        results: List[Dict[str, Any]] = []
        raw_docs: List[Dict[str, Any]] = []
        if not urls:
            emit_log("discovery.fetch.skipped", extra={"reason": "empty_url_list"})
            return {"discovered": [], "raw_documents": []}
        PIPELINE_GAUGE.inc()
        try:
            coros = [
                _fetch_single(fetcher, cache, url, config.get("site_key")) for url in urls
            ]
            for payload in await asyncio.gather(*coros, return_exceptions=True):
                if isinstance(payload, Exception):
                    emit_log("discovery.fetch.error", extra={"error": str(payload)}, level=40)
                    continue
                raw_docs.append(payload)
        finally:
            PIPELINE_GAUGE.dec()
        for doc in raw_docs:
            parsed = parser.parse(doc.get("html", ""), url=doc.get("url")) if doc.get("html") else {}
            merged = {**doc, "parsed": parsed}
            results.append(merged)
        return {"discovered": results, "raw_documents": raw_docs}

    graph.add_node("fetch", fetch_node)
    graph.set_entry_point("fetch")
    return graph


async def _fetch_single(
    fetcher: PageFetcher,
    cache: Optional[StorageAdapter],
    url: str,
    site_key: Optional[str],
) -> Dict[str, Any]:
    site_label = site_key or "default"
    REQUEST_COUNTER.labels(site_label).inc()
    with REQUEST_LATENCY.labels(site_label).time():
        try:
            with traced_span("discovery.fetch", {"url": url}):
                result = await fetcher.fetch(url, context={"site": site_label})
        except Exception as exc:
            REQUEST_FAILURE.labels(site_label).inc()
            emit_log("discovery.fetch.failure", extra={"url": url, "error": str(exc)})
            raise
    if cache:
        cache.put(f"raw:{url}", result, ttl=cache and 3600)
    return result


__all__ = ["build_discovery_graph", "DiscoveryState"]
