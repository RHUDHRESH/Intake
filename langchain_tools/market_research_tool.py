"""LangChain tool wrapping the market research orchestrator."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from Intake.market_research import ConfigManager
from Intake.market_research.fetchers import FallbackPageFetcher, PlaywrightFetcher, RequestsFetcher
from Intake.market_research.nlp import EmbeddingNLPAnalyzer
from Intake.market_research.parsers import SoupHTMLParser
from Intake.market_research.storage import ChromaVectorIndexAdapter, InMemoryStorageAdapter
from Intake.market_research.workflows.orchestrator import build_market_research_orchestrator


class MarketResearchInput(BaseModel):
    config_path: Path = Field(..., description="Path to market research config (YAML/JSON)")
    site_key: str = Field("default", description="Site key inside config")
    seed_urls: Optional[List[str]] = Field(None, description="Override seed URLs")


class MarketResearchAgentTool(BaseTool):
    name: str = "market_research_agent"
    description: str = "Deep market research orchestrator with discovery and analysis subgraphs."
    args_schema: type = MarketResearchInput

    def _run(self, config_path: Path, site_key: str = "default", seed_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task instead
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._arun(config_path=config_path, site_key=site_key, seed_urls=seed_urls)
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to call asyncio.run
            return asyncio.run(self._arun(config_path=config_path, site_key=site_key, seed_urls=seed_urls))

    async def _arun(
        self,
        *,
        config_path: Path,
        site_key: str = "default",
        seed_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        manager = ConfigManager(config_path)
        cache = InMemoryStorageAdapter()
        fetcher = FallbackPageFetcher([
            PlaywrightFetcher(),
            RequestsFetcher(cache=cache, rate_limit_per_sec=5),
        ])
        parser = SoupHTMLParser()
        analyzer = EmbeddingNLPAnalyzer()
        index = ChromaVectorIndexAdapter()
        graph = build_market_research_orchestrator(
            config_manager=manager,
            fetcher=fetcher,
            parser=parser,
            analyzer=analyzer,
            index=index,
            cache=cache,
        )
        compiled = graph.compile()
        payload = {"site_key": site_key}
        if seed_urls:
            payload["seed_urls"] = seed_urls
        return compiled.invoke(payload)


__all__ = ["MarketResearchAgentTool"]
