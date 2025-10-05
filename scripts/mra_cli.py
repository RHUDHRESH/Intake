#!/usr/bin/env python3
"""
Market Research Agent CLI for configuration and execution.

This CLI provides a command-line interface for:
- Configuring market research agents
- Running market research operations
- Managing research results and storage
- Testing fallback mechanisms
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Intake.market_research.agent import MarketResearchAgent, MarketResearchConfig, create_market_research_agent
from Intake.market_research.fetchers import RequestsFetcher
from Intake.market_research.parsers import BeautifulSoupParser
from Intake.market_research.nlp import SimpleNLPAnalyzer
from Intake.market_research.storage import JSONStorageAdapter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketResearchCLI:
    """CLI for market research operations."""

    def __init__(self):
        self.config_file = Path("market_research_config.json")
        self.results_dir = Path("research_results")
        self.results_dir.mkdir(exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {self.config_file}")

    def create_agent_from_config(self, config: Dict[str, Any]) -> MarketResearchAgent:
        """Create market research agent from configuration."""
        # Extract agent config
        agent_config = config.get("agent", {})

        # Create dependencies if configured
        dependencies = {}

        if config.get("use_real_dependencies", False):
            # Use real implementations
            dependencies.update({
                "page_fetcher": RequestsFetcher(
                    timeout=agent_config.get("request_timeout", 30.0),
                    circuit_breaker=None,  # Agent will create its own
                    bulkhead=None
                ),
                "html_parser": BeautifulSoupParser(),
                "nlp_analyzer": SimpleNLPAnalyzer(),
                "storage_adapter": JSONStorageAdapter(base_path=str(self.results_dir))
            })
        else:
            # Use mock/None dependencies for testing
            logger.info("Using mock dependencies - agent will rely on fallback mechanisms")

        # Create agent config
        mra_config = MarketResearchConfig(
            max_concurrent_requests=agent_config.get("max_concurrent_requests", 5),
            request_timeout=agent_config.get("request_timeout", 30.0),
            retry_attempts=agent_config.get("retry_attempts", 3),
            circuit_breaker_threshold=agent_config.get("circuit_breaker_threshold", 5),
            fallback_to_mock=agent_config.get("fallback_to_mock", True),
            enable_caching=agent_config.get("enable_caching", True),
            cache_ttl=agent_config.get("cache_ttl", 3600)
        )

        return create_market_research_agent(
            config=mra_config,
            **dependencies
        )

    async def run_research(self, args) -> int:
        """Run market research operation."""
        try:
            # Load configuration
            config = self.load_config()

            # Create agent
            agent = self.create_agent_from_config(config)

            # Log capabilities
            capabilities = agent.get_research_capabilities()
            logger.info("Agent capabilities: %s", json.dumps(capabilities, indent=2))

            # Run research
            logger.info(f"Starting research: {args.query}")
            result = await agent.research_market(
                query=args.query,
                research_type=args.research_type,
                use_fallback=not args.no_fallback
            )

            # Display results
            print(f"\n{'='*50}")
            print("RESEARCH RESULTS")
            print(f"{'='*50}")
            print(f"Query: {result.metadata.get('query', 'N/A')}")
            print(f"Research Type: {result.metadata.get('research_type', 'N/A')}")
            print(f"Success: {result.success}")
            print(f"Execution Time: {result.execution_time:.2f}s")
            print(f"Fallback Used: {result.fallback_used}")
            print(f"Method: {result.metadata.get('method', 'N/A')}")

            if result.errors:
                print(f"\nErrors/Warnings:")
                for error in result.errors:
                    print(f"  - {error}")

            print(f"\nData:")
            print(json.dumps(result.data, indent=2))

            # Save results if requested
            if args.save_results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"research_{args.research_type}_{timestamp}.json"
                filepath = self.results_dir / filename

                with open(filepath, 'w') as f:
                    json.dump({
                        "result": result,
                        "saved_at": datetime.now().isoformat(),
                        "cli_args": vars(args)
                    }, f, indent=2, default=str)

                print(f"\nResults saved to: {filepath}")

            return 0 if result.success else 1

        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            return 1

    async def configure_agent(self, args) -> int:
        """Configure market research agent."""
        try:
            # Load existing config or create new one
            config = self.load_config()

            if not config.get("agent"):
                config["agent"] = {}

            # Update configuration based on args
            if args.max_concurrent is not None:
                config["agent"]["max_concurrent_requests"] = args.max_concurrent

            if args.timeout is not None:
                config["agent"]["request_timeout"] = args.timeout

            if args.retry_attempts is not None:
                config["agent"]["retry_attempts"] = args.retry_attempts

            if args.circuit_breaker_threshold is not None:
                config["agent"]["circuit_breaker_threshold"] = args.circuit_breaker_threshold

            if args.fallback is not None:
                config["agent"]["fallback_to_mock"] = args.fallback

            if args.caching is not None:
                config["agent"]["enable_caching"] = args.caching

            if args.cache_ttl is not None:
                config["agent"]["cache_ttl"] = args.cache_ttl

            if args.use_real_dependencies is not None:
                config["use_real_dependencies"] = args.use_real_dependencies

            # Save configuration
            self.save_config(config)

            # Display current configuration
            print("Current Configuration:")
            print(json.dumps(config, indent=2))

            return 0

        except Exception as e:
            logger.error(f"Configuration failed: {str(e)}")
            return 1

    async def show_capabilities(self, args) -> int:
        """Show agent capabilities."""
        try:
            config = self.load_config()
            agent = self.create_agent_from_config(config)

            capabilities = agent.get_research_capabilities()
            print(json.dumps(capabilities, indent=2))

            return 0

        except Exception as e:
            logger.error(f"Failed to show capabilities: {str(e)}")
            return 1

    async def test_fallback(self, args) -> int:
        """Test fallback mechanisms."""
        try:
            config = self.load_config()
            agent = self.create_agent_from_config(config)

            # Test with no dependencies to force fallback
            test_agent = MarketResearchAgent(
                config=MarketResearchConfig(fallback_to_mock=True),
                page_fetcher=None,  # Force fallback
                html_parser=None,
                nlp_analyzer=None
            )

            logger.info("Testing fallback mechanisms...")
            result = await test_agent.research_market(
                query=args.query or "test query",
                research_type=args.research_type or "comprehensive",
                use_fallback=True
            )

            print(f"Fallback Test Results:")
            print(f"Success: {result.success}")
            print(f"Fallback Used: {result.fallback_used}")
            print(f"Method: {result.metadata.get('method', 'N/A')}")

            if result.data:
                print(f"Data Preview: {json.dumps(result.data, indent=2)[:500]}...")

            return 0 if result.success and result.fallback_used else 1

        except Exception as e:
            logger.error(f"Fallback test failed: {str(e)}")
            return 1

    async def list_results(self, args) -> int:
        """List stored research results."""
        try:
            results = list(self.results_dir.glob("research_*.json"))
            results.sort(reverse=True)  # Most recent first

            if not results:
                print("No research results found.")
                return 0

            print(f"Found {len(results)} research results:")
            print("-" * 80)

            for result_file in results[:args.limit]:
                try:
                    with open(result_file, 'r') as f:
                        data = json.load(f)

                    result = data.get("result", {})
                    metadata = result.get("metadata", {})

                    print(f"File: {result_file.name}")
                    print(f"  Query: {metadata.get('query', 'N/A')}")
                    print(f"  Type: {metadata.get('research_type', 'N/A')}")
                    print(f"  Method: {metadata.get('method', 'N/A')}")
                    print(f"  Success: {result.get('success', False)}")
                    print(f"  Execution Time: {result.get('execution_time', 0):.2f}s")
                    print(f"  Saved: {data.get('saved_at', 'N/A')}")
                    print()

                except Exception as e:
                    logger.warning(f"Failed to read {result_file}: {str(e)}")

            return 0

        except Exception as e:
            logger.error(f"Failed to list results: {str(e)}")
            return 1

    async def run_async_command(self, args) -> int:
        """Run async CLI commands."""
        if args.command == "research":
            return await self.run_research(args)
        elif args.command == "configure":
            return await self.configure_agent(args)
        elif args.command == "capabilities":
            return await self.show_capabilities(args)
        elif args.command == "test-fallback":
            return await self.test_fallback(args)
        elif args.command == "list-results":
            return await self.list_results(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Market Research Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mra_cli.py research "AI market trends" --research-type trends --save-results
  python mra_cli.py configure --max-concurrent 10 --timeout 60
  python mra_cli.py test-fallback "test query"
  python mra_cli.py list-results --limit 5
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Research command
    research_parser = subparsers.add_parser("research", help="Run market research")
    research_parser.add_argument("query", help="Research query")
    research_parser.add_argument(
        "--research-type",
        choices=["competitor", "market_size", "trends", "comprehensive"],
        default="comprehensive",
        help="Type of research to perform"
    )
    research_parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback mechanisms"
    )
    research_parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save results to file"
    )

    # Configure command
    config_parser = subparsers.add_parser("configure", help="Configure agent")
    config_parser.add_argument("--max-concurrent", type=int, help="Max concurrent requests")
    config_parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    config_parser.add_argument("--retry-attempts", type=int, help="Number of retry attempts")
    config_parser.add_argument("--circuit-breaker-threshold", type=int, help="Circuit breaker failure threshold")
    config_parser.add_argument("--fallback", type=bool, help="Enable/disable fallback")
    config_parser.add_argument("--caching", type=bool, help="Enable/disable caching")
    config_parser.add_argument("--cache-ttl", type=int, help="Cache TTL in seconds")
    config_parser.add_argument("--use-real-dependencies", type=bool, help="Use real dependencies instead of mocks")

    # Capabilities command
    capabilities_parser = subparsers.add_parser("capabilities", help="Show agent capabilities")

    # Test fallback command
    fallback_parser = subparsers.add_parser("test-fallback", help="Test fallback mechanisms")
    fallback_parser.add_argument("query", nargs="?", help="Test query (optional)")
    fallback_parser.add_argument("--research-type", default="comprehensive", help="Research type for test")

    # List results command
    list_parser = subparsers.add_parser("list-results", help="List stored research results")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results to show")

    return parser

async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cli = MarketResearchCLI()
    exit_code = await cli.run_async_command(args)

    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
