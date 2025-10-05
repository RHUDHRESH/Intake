"""LangGraph orchestration for marketing intake workflows."""
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledGraph

from Intake.langchain_tools.web_crawler_tool import WebCrawlerTool


class MarketingState(TypedDict, total=False):
    urls: List[str]
    crawl_results: List[Dict[str, Any]]


def build_marketing_graph(
    *,
    crawler_tool: Optional[WebCrawlerTool] = None,
) -> StateGraph:
    """Construct a LangGraph state machine for the marketing workflow.

    Parameters
    ----------
    crawler_tool: Optional[WebCrawlerTool]
        Custom crawler tool instance. If omitted a default WebCrawlerTool is used.
    """

    tool = crawler_tool or WebCrawlerTool()
    graph = StateGraph(MarketingState)

    async def crawl_node(state: MarketingState) -> MarketingState:
        urls = state.get("urls", []) or []
        results: List[Dict[str, Any]] = []
        for url in urls:
            output = await tool.arun(url=url)
            results.append(output)
        return {"crawl_results": results}

    graph.add_node("crawl_web", crawl_node)
    graph.add_edge(START, "crawl_web")
    graph.add_edge("crawl_web", END)
    return graph


def compile_marketing_graph(**kwargs) -> CompiledGraph:
    """Convenience helper returning the compiled LangGraph workflow."""
    graph = build_marketing_graph(**kwargs)
    return graph.compile()
