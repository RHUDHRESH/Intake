"""
MarketResearchAgent with dependency injection and fallback mechanisms.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .interfaces import (
    PageFetcher, HTMLParser, NLPAnalyzer, StorageAdapter,
    VectorIndexAdapter, ConfigProvider
)
from .resilience import CircuitBreaker, BulkheadExecutor
from ..core.retry import RetryPolicy, with_retry
from ..core.mixins import ConfigurableMixin

logger = logging.getLogger(__name__)

@dataclass
class MarketResearchConfig:
    """Configuration for market research operations."""
    max_concurrent_requests: int = 5
    request_timeout: float = 30.0
    retry_attempts: int = 3
    circuit_breaker_threshold: int = 5
    fallback_to_mock: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600

@dataclass
class ResearchResult:
    """Result of market research operation."""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    fallback_used: bool = False

class MarketResearchAgent(ConfigurableMixin):
    """
    Market research agent with dependency injection and comprehensive fallback mechanisms.
    """

    def __init__(
        self,
        config: Optional[MarketResearchConfig] = None,
        page_fetcher: Optional[PageFetcher] = None,
        html_parser: Optional[HTMLParser] = None,
        nlp_analyzer: Optional[NLPAnalyzer] = None,
        storage_adapter: Optional[StorageAdapter] = None,
        vector_adapter: Optional[VectorIndexAdapter] = None,
        config_provider: Optional[ConfigProvider] = None,
    ):
        """Initialize the market research agent with dependency injection."""
        super().__init__(config or MarketResearchConfig())

        # Core dependencies
        self.page_fetcher = page_fetcher
        self.html_parser = html_parser
        self.nlp_analyzer = nlp_analyzer
        self.storage_adapter = storage_adapter
        self.vector_adapter = vector_adapter
        self.config_provider = config_provider

        # Resilience components
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.get_config("circuit_breaker_threshold", 5),
            recovery_timeout=30.0
        )
        self.bulkhead = BulkheadExecutor(
            max_concurrency=self.get_config("max_concurrent_requests", 5)
        )

        # Fallback mechanisms
        self.fallback_data = self._load_fallback_data()
        self.mock_responses = self._load_mock_responses()

        logger.info("MarketResearchAgent initialized with dependency injection")

    def _load_fallback_data(self) -> Dict[str, Any]:
        """Load fallback data for when external services fail."""
        return {
            "competitor_analysis": {
                "methodology": "mock_fallback",
                "competitors": [
                    {"name": "Competitor A", "market_share": "15%", "strengths": ["Brand recognition", "Distribution"]},
                    {"name": "Competitor B", "market_share": "12%", "strengths": ["Technology", "Innovation"]},
                    {"name": "Competitor C", "market_share": "8%", "strengths": ["Customer service", "Pricing"]}
                ],
                "market_trends": ["Digital transformation", "Sustainability focus", "Remote work adoption"]
            },
            "market_size": {
                "total_addressable_market": "$50B",
                "serviceable_available_market": "$15B",
                "serviceable_obtainable_market": "$3B",
                "growth_rate": "12% CAGR"
            },
            "customer_insights": {
                "pain_points": ["High costs", "Complex implementation", "Poor support"],
                "desired_features": ["Ease of use", "Integration capabilities", "24/7 support"],
                "purchase_criteria": ["ROI potential", "Implementation time", "Vendor reputation"]
            }
        }

    def _load_mock_responses(self) -> Dict[str, Any]:
        """Load mock responses for testing and fallback scenarios."""
        return {
            "web_search": {
                "results": [
                    {"title": "Market Analysis Report", "url": "https://example.com/report", "snippet": "Key market insights..."},
                    {"title": "Industry Trends 2024", "url": "https://example.com/trends", "snippet": "Latest industry developments..."}
                ],
                "total_results": 150
            },
            "competitor_analysis": {
                "competitors": [
                    {"name": "TechCorp", "website": "https://techcorp.com", "description": "Leading technology solutions provider"},
                    {"name": "InnovateLabs", "website": "https://innovatelabs.com", "description": "Innovation-focused competitor"}
                ]
            }
        }

    async def research_market(
        self,
        query: str,
        research_type: str = "comprehensive",
        use_fallback: bool = True
    ) -> ResearchResult:
        """
        Perform comprehensive market research with fallback mechanisms.

        Args:
            query: Research query or topic
            research_type: Type of research ("competitor", "market_size", "trends", "comprehensive")
            use_fallback: Whether to use fallback data if primary research fails

        Returns:
            ResearchResult with data, metadata, and error information
        """
        start_time = datetime.now()
        errors = []

        try:
            # Try primary research with circuit breaker protection
            async def _primary_research():
                return await self._execute_primary_research(query, research_type)

            result_data = await self.circuit_breaker.run(_primary_research)

            execution_time = (datetime.now() - start_time).total_seconds()

            return ResearchResult(
                success=True,
                data=result_data,
                metadata={
                    "query": query,
                    "research_type": research_type,
                    "method": "primary",
                    "timestamp": datetime.now().isoformat()
                },
                execution_time=execution_time,
                fallback_used=False
            )

        except Exception as e:
            logger.warning(f"Primary research failed for query '{query}': {str(e)}")
            errors.append(str(e))

            # Try fallback if enabled
            if use_fallback and self.get_flag("fallback_to_mock", True):
                try:
                    fallback_data = await self._execute_fallback_research(query, research_type)
                    execution_time = (datetime.now() - start_time).total_seconds()

                    return ResearchResult(
                        success=True,
                        data=fallback_data,
                        metadata={
                            "query": query,
                            "research_type": research_type,
                            "method": "fallback",
                            "timestamp": datetime.now().isoformat(),
                            "original_errors": errors
                        },
                        execution_time=execution_time,
                        fallback_used=True,
                        errors=errors
                    )

                except Exception as fallback_error:
                    logger.error(f"Fallback research also failed: {str(fallback_error)}")
                    errors.append(f"Fallback error: {str(fallback_error)}")

            # Return failed result
            execution_time = (datetime.now() - start_time).total_seconds()
            return ResearchResult(
                success=False,
                data={},
                metadata={
                    "query": query,
                    "research_type": research_type,
                    "method": "failed",
                    "timestamp": datetime.now().isoformat()
                },
                execution_time=execution_time,
                errors=errors
            )

    async def _execute_primary_research(self, query: str, research_type: str) -> Dict[str, Any]:
        """Execute primary research using injected dependencies."""
        if not self.page_fetcher or not self.html_parser or not self.nlp_analyzer:
            raise RuntimeError("Required dependencies not injected: page_fetcher, html_parser, nlp_analyzer")

        # Execute research pipeline with bulkhead protection
        async def _research_pipeline():
            # Step 1: Search and fetch relevant pages
            search_results = await self._search_and_fetch(query, research_type)

            # Step 2: Parse and extract content
            parsed_content = await self._parse_content(search_results)

            # Step 3: Analyze content with NLP
            analysis_results = await self._analyze_content(parsed_content)

            # Step 4: Synthesize results
            synthesized = self._synthesize_results(analysis_results, research_type)

            return synthesized

        return await self.bulkhead.run(_research_pipeline)

    async def _search_and_fetch(self, query: str, research_type: str) -> List[Dict[str, Any]]:
        """Search for and fetch relevant web content."""
        # This would integrate with search APIs in a real implementation
        # For now, return mock search results
        mock_urls = [
            f"https://example.com/{research_type}/{i}" for i in range(3)
        ]

        fetch_tasks = []
        for url in mock_urls:
            async def _fetch_url(url=url):
                return await self.page_fetcher.fetch(url)

            fetch_tasks.append(_fetch_url())

        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Filter out exceptions and return successful fetches
        successful_fetches = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {mock_urls[i]}: {str(result)}")
            else:
                successful_fetches.append(result)

        return successful_fetches

    async def _parse_content(self, fetch_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse HTML content from fetch results."""
        parsed_results = []

        for fetch_result in fetch_results:
            html_content = fetch_result.get("html", "")
            url = fetch_result.get("url", "")

            try:
                parsed = self.html_parser.parse(html_content, url=url)
                parsed_results.append(parsed)
            except Exception as e:
                logger.warning(f"Failed to parse content from {url}: {str(e)}")
                # Return basic structure if parsing fails
                parsed_results.append({
                    "url": url,
                    "title": "Parse Error",
                    "content": html_content[:500] + "..." if len(html_content) > 500 else html_content,
                    "error": str(e)
                })

        return parsed_results

    async def _analyze_content(self, parsed_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze parsed content using NLP."""
        # Extract text content for analysis
        texts = []
        metadata = []

        for item in parsed_content:
            content = item.get("content", "")
            if content:
                texts.append(content)
                metadata.append({
                    "url": item.get("url"),
                    "title": item.get("title")
                })

        if not texts:
            return {"error": "No content to analyze"}

        # Run NLP analysis
        analysis = self.nlp_analyzer.analyze(texts, metadata=metadata)

        return analysis

    def _synthesize_results(self, analysis: Dict[str, Any], research_type: str) -> Dict[str, Any]:
        """Synthesize analysis results into research findings."""
        # This would contain sophisticated synthesis logic
        # For now, return structured mock results

        synthesis = {
            "research_type": research_type,
            "analysis_summary": analysis.get("summary", {}),
            "key_findings": analysis.get("findings", []),
            "confidence_score": analysis.get("confidence", 0.7),
            "recommendations": analysis.get("recommendations", []),
            "sources_analyzed": len(analysis.get("sources", [])),
            "synthesis_method": "dependency_injection_pipeline"
        }

        return synthesis

    async def _execute_fallback_research(self, query: str, research_type: str) -> Dict[str, Any]:
        """Execute fallback research using mock data."""
        logger.info(f"Using fallback research for query: {query}, type: {research_type}")

        # Return appropriate fallback data based on research type
        fallback_key = f"{research_type}_analysis" if research_type != "comprehensive" else "competitor_analysis"

        fallback_data = self.fallback_data.get(fallback_key, self.fallback_data["competitor_analysis"])

        return {
            "query": query,
            "research_type": research_type,
            "method": "fallback",
            "data": fallback_data,
            "confidence": 0.3,  # Lower confidence for fallback data
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "This is fallback/mock data. Primary research sources were unavailable."
        }

    async def store_research_results(self, result: ResearchResult) -> str:
        """Store research results using storage adapter."""
        if not self.storage_adapter:
            logger.warning("No storage adapter available, skipping storage")
            return "no_storage_adapter"

        try:
            key = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(result.metadata.get('query', ''))}"
            await self.storage_adapter.put(key, {
                "result": result,
                "stored_at": datetime.now().isoformat()
            })
            return key
        except Exception as e:
            logger.error(f"Failed to store research results: {str(e)}")
            return "storage_error"

    async def retrieve_research_results(self, key: str) -> Optional[ResearchResult]:
        """Retrieve stored research results."""
        if not self.storage_adapter:
            return None

        try:
            stored = await self.storage_adapter.get(key)
            if stored:
                return stored.get("result")
        except Exception as e:
            logger.error(f"Failed to retrieve research results: {str(e)}")

        return None

    def get_research_capabilities(self) -> Dict[str, Any]:
        """Get information about available research capabilities."""
        return {
            "dependencies_injected": {
                "page_fetcher": self.page_fetcher is not None,
                "html_parser": self.html_parser is not None,
                "nlp_analyzer": self.nlp_analyzer is not None,
                "storage_adapter": self.storage_adapter is not None,
                "vector_adapter": self.vector_adapter is not None,
                "config_provider": self.config_provider is not None
            },
            "resilience_features": {
                "circuit_breaker_enabled": True,
                "bulkhead_concurrency": self.get_config("max_concurrent_requests", 5),
                "retry_attempts": self.get_config("retry_attempts", 3),
                "fallback_available": self.get_flag("fallback_to_mock", True)
            },
            "supported_research_types": [
                "competitor",
                "market_size",
                "trends",
                "comprehensive"
            ],
            "cache_settings": {
                "enabled": self.get_flag("enable_caching", True),
                "ttl_seconds": self.get_config("cache_ttl", 3600)
            }
        }

# Factory function for easy agent creation
def create_market_research_agent(
    config: Optional[MarketResearchConfig] = None,
    **dependency_overrides
) -> MarketResearchAgent:
    """
    Factory function to create MarketResearchAgent with optional dependency overrides.

    Args:
        config: Configuration object
        **dependency_overrides: Override any dependencies (e.g., page_fetcher=custom_fetcher)

    Returns:
        Configured MarketResearchAgent instance
    """
    return MarketResearchAgent(
        config=config,
        **dependency_overrides
    )
