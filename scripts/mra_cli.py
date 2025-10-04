from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from market_research import ConfigManager
from market_research.fetchers import FallbackPageFetcher, PlaywrightFetcher, RequestsFetcher
from market_research.parsers import SoupHTMLParser
from market_research.storage import ChromaVectorIndexAdapter, InMemoryStorageAdapter
from market_research.workflows.orchestrator import build_market_research_orchestrator
from position_validator import (
    AdaptScoringModule,
    GodinScoringModule,
    OgilvyScoringModule,
    PositionValidatorEngine,
    Switch6ScoringModule,
)
from position_validator.engine import ModuleConfig


def _load_modules():
    return [
        AdaptScoringModule(),
        Switch6ScoringModule(),
        OgilvyScoringModule(),
        GodinScoringModule(),
    ]


def run_market_research(args: argparse.Namespace) -> None:
    config_path = Path(args.config)
    config_manager = ConfigManager(config_path)
    cache = InMemoryStorageAdapter()
    fetcher = FallbackPageFetcher([
        PlaywrightFetcher(),
        RequestsFetcher(cache=cache, rate_limit_per_sec=args.rate_limit),
    ])
    parser = SoupHTMLParser()
    from market_research.nlp import EmbeddingNLPAnalyzer

    analyzer = EmbeddingNLPAnalyzer()
    index = ChromaVectorIndexAdapter()
    graph = build_market_research_orchestrator(
        config_manager=config_manager,
        fetcher=fetcher,
        parser=parser,
        analyzer=analyzer,
        index=index,
        cache=cache,
    )
    compiled = graph.compile()
    payload = {
        "seed_urls": args.urls,
        "site_key": args.site_key,
    }
    result = compiled.invoke(payload)
    print(json.dumps(result, indent=2))


def validate_config(args: argparse.Namespace) -> None:
    config_path = Path(args.config)
    manager = ConfigManager(config_path)
    data = manager.get()
    required_keys = {"sites"}
    missing = required_keys - data.keys()
    if missing:
        print(f"Config missing keys: {', '.join(sorted(missing))}")
        sys.exit(1)
    for name, site in data["sites"].items():
        if "seed_urls" not in site:
            print(f"Site {name} missing seed_urls")
            sys.exit(2)
    print("Config valid ?")


def scaffold_config(args: argparse.Namespace) -> None:
    template = {
        "sites": {
            "saas": {
                "seed_urls": ["https://example.com"],
                "rate_limit": 3,
            },
            "ecommerce": {
                "seed_urls": ["https://shop.example.com"],
                "rate_limit": 2,
            },
        }
    }
    Path(args.output).write_text(json.dumps(template, indent=2), encoding="utf-8")
    print(f"Wrote template config to {args.output}")


def score_statement(args: argparse.Namespace) -> None:
    engine = PositionValidatorEngine(_load_modules())
    overrides: Dict[str, ModuleConfig] = {}
    if args.weights:
        for chunk in args.weights:
            module, weight = chunk.split("=", 1)
            overrides[module] = ModuleConfig(name=module, weight=float(weight))
    result = engine.score(args.statement, module_overrides=overrides)
    print(json.dumps(result, indent=2))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Market Research Agent CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run market research workflow")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--urls", nargs="*", default=[])
    run_parser.add_argument("--site-key", default="default")
    run_parser.add_argument("--rate-limit", type=int, default=5)
    run_parser.set_defaults(func=run_market_research)

    validate_parser = sub.add_parser("validate-config", help="Validate config file")
    validate_parser.add_argument("--config", required=True)
    validate_parser.set_defaults(func=validate_config)

    scaffold_parser = sub.add_parser("scaffold-config", help="Create config template")
    scaffold_parser.add_argument("--output", default="market_agent.config.json")
    scaffold_parser.set_defaults(func=scaffold_config)

    score_parser = sub.add_parser("score", help="Score a positioning statement")
    score_parser.add_argument("statement", help="Statement to evaluate")
    score_parser.add_argument("--weights", nargs="*", help="Per-module weight overrides (module=weight)")
    score_parser.set_defaults(func=score_statement)

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()

