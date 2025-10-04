from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from ..config import ConfigManager
from ..interfaces import HTMLParser, NLPAnalyzer, PageFetcher, StorageAdapter, VectorIndexAdapter
from ..telemetry import emit_log
from .analysis_graph import AnalysisState, build_analysis_graph
from .discovery_graph import DiscoveryState, build_discovery_graph


class OrchestratorState(TypedDict, total=False):
    request_id: str
    site_key: str
    config: Dict[str, Any]
    seed_urls: List[str]
    discovery: Dict[str, Any]
    analysis: Dict[str, Any]


def build_market_research_orchestrator(
    *,
    config_manager: ConfigManager,
    fetcher: PageFetcher,
    parser: HTMLParser,
    analyzer: NLPAnalyzer,
    index: VectorIndexAdapter,
    cache: Optional[StorageAdapter] = None,
) -> StateGraph:
    discovery_graph = build_discovery_graph(fetcher=fetcher, parser=parser, cache=cache)
    analysis_graph = build_analysis_graph(analyzer=analyzer, index=index)
    compiled_discovery = discovery_graph.compile()
    compiled_analysis = analysis_graph.compile()

    graph = StateGraph(OrchestratorState)

    def initialise_node(state: OrchestratorState) -> OrchestratorState:
        request_id = state.get("request_id") or str(uuid.uuid4())
        site_key = state.get("site_key") or "default"
        config = config_manager.get()
        site_config = config.get("sites", {}).get(site_key, {})
        seed_urls = state.get("seed_urls") or site_config.get("seed_urls", [])
        emit_log("orchestrator.initialised", extra={"request_id": request_id, "site_key": site_key})
        return {
            "request_id": request_id,
            "site_key": site_key,
            "config": site_config,
            "seed_urls": seed_urls,
        }

    async def discovery_node(state: OrchestratorState) -> OrchestratorState:
        payload: DiscoveryState = {
            "seed_urls": state.get("seed_urls", []),
            "config": {"site_key": state.get("site_key")},
        }
        result = await compiled_discovery.ainvoke(payload)
        emit_log("orchestrator.discovery.completed", extra={"request_id": state["request_id"], "count": len(result.get("discovered", []))})
        return {"discovery": result}

    async def analysis_node(state: OrchestratorState) -> OrchestratorState:
        discovered = state.get("discovery", {}).get("discovered", [])
        payload: AnalysisState = {"documents": discovered}
        result = await compiled_analysis.ainvoke(payload)
        emit_log("orchestrator.analysis.completed", extra={"request_id": state["request_id"], "indexed": result.get("indexed")})
        return {"analysis": result}

    graph.add_node("initialise", initialise_node)
    graph.add_node("run_discovery", discovery_node)
    graph.add_node("run_analysis", analysis_node)

    graph.add_edge(START, "initialise")
    graph.add_conditional_edges(
        "initialise",
        lambda state: "run_discovery" if state.get("seed_urls") else END,
        {"run_discovery": "run_discovery", END: END},
    )
    graph.add_edge("run_discovery", "run_analysis")
    graph.add_edge("run_analysis", END)

    return graph


__all__ = ["OrchestratorState", "build_market_research_orchestrator"]
