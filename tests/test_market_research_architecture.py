import asyncio
import json
import time
from pathlib import Path

import pytest

from market_research.config import ConfigManager
from market_research.parsers import SoupHTMLParser
from market_research.resilience import CircuitBreaker, CircuitBreakerOpen
from market_research.storage import InMemoryStorageAdapter
from market_research.workflows.orchestrator import build_market_research_orchestrator
from market_research.nlp import EmbeddingNLPAnalyzer


@pytest.mark.asyncio
async def test_orchestrator_skips_when_no_seeds(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"sites": {"default": {"seed_urls": []}}}))
    manager = ConfigManager(config_path, auto_reload=False)
    cache = InMemoryStorageAdapter()

    class StubFetcher:
        async def fetch(self, url: str, *, context=None):
            return {
                "url": url,
                "status": 200,
                "html": "<html><body>Example</body></html>",
                "source": "stub",
            }

    fetcher = StubFetcher()
    parser = SoupHTMLParser()
    analyzer = EmbeddingNLPAnalyzer()

    class StubIndex:
        def __init__(self):
            self.documents = []

        def upsert(self, documents):
            self.documents.extend(documents)

        def query(self, query_text, *, top_k=5, filters=None):
            return []

    index = StubIndex()

    graph = build_market_research_orchestrator(
        config_manager=manager,
        fetcher=fetcher,
        parser=parser,
        analyzer=analyzer,
        index=index,
        cache=cache,
    )
    compiled = graph.compile()
    result = compiled.invoke({"seed_urls": []})
    assert "analysis" not in result


def test_config_manager_auto_reload(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("sites:\n  default:\n    seed_urls: ['https://example.com']\n")
    manager = ConfigManager(config_path, reload_interval=0.1)
    first = manager.get()
    assert first["sites"]["default"]["seed_urls"]
    time.sleep(0.2)
    config_path.write_text("sites:\n  default:\n    seed_urls: ['https://updated.example.com']\n")
    second = manager.get()
    assert second["sites"]["default"]["seed_urls"][0].endswith("updated.example.com")


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    async def failing():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await breaker.run(failing)
    with pytest.raises(CircuitBreakerOpen):
        await breaker.run(lambda: asyncio.sleep(0))
    await asyncio.sleep(0.2)
    await breaker.run(lambda: asyncio.sleep(0))
