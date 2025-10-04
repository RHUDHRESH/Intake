"""LangGraph orchestration for the Ogilvy Big Idea pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledGraph
from langgraph.pregel.retry import RetryPolicy

from frameworks.big_idea_pipeline import (
    BigIdeaPipeline,
    BigIdeaRequest,
)


class BigIdeaState(TypedDict, total=False):
    """State payload passed between LangGraph nodes."""

    request: BigIdeaRequest
    request_payload: Dict[str, Any]
    inspirations: List[Dict[str, Any]]
    prompt: str
    generated_headlines: List[str]
    clarity: List[Dict[str, Any]]
    mockups: List[Dict[str, Any]]
    claim_reviews: List[Dict[str, Any]]
    assembled_headlines: List[Dict[str, Any]]
    dashboard: Dict[str, Any]


@dataclass
class BigIdeaDependencies:
    """Container exposing the pipeline components for graph nodes."""

    pipeline: BigIdeaPipeline

    @property
    def knowledge_base(self):
        return self.pipeline.knowledge_base

    @property
    def generator(self):
        return self.pipeline.generator

    @property
    def clarity(self):
        return self.pipeline.clarity_analyzer

    @property
    def mockups(self):
        return self.pipeline.mockup_service

    @property
    def claims(self):
        return self.pipeline.claim_validator


def _default_dependencies() -> BigIdeaDependencies:
    pipeline = BigIdeaPipeline()
    return BigIdeaDependencies(pipeline=pipeline)


def build_big_idea_graph(*, dependencies: Optional[BigIdeaDependencies] = None) -> StateGraph:
    """Construct the LangGraph workflow for Big Idea generation."""

    deps = dependencies or _default_dependencies()
    graph = StateGraph(BigIdeaState)

    def _ensure_request(state: BigIdeaState) -> BigIdeaState:
        request = state.get("request")
        if isinstance(request, BigIdeaRequest):
            return {"request": request}

        payload: Dict[str, Any] = {}
        if isinstance(state.get("request_payload"), dict):
            payload = state["request_payload"]
        elif isinstance(state.get("request"), dict):
            payload = state["request"]  # type: ignore[assignment]

        if not payload:
            raise ValueError("BigIdeaGraph requires a request payload")

        request_obj = BigIdeaRequest(
            brand=payload.get("brand") or payload.get("brand_name") or "Your Brand",
            positioning_statement=payload.get("positioning_statement") or payload.get("positioning") or "",
            audience=payload.get("audience") or payload.get("target") or payload.get("target_description", "Customers"),
            benefit=payload.get("benefit") or payload.get("primary_benefit") or "Results",
            emotional_hook=payload.get("emotional_hook"),
            product=payload.get("product"),
            benchmarks=payload.get("benchmarks"),
            brand_voice=payload.get("brand_voice"),
            style=payload.get("style"),
        )
        return {"request": request_obj}

    def retrieve_examples(state: BigIdeaState) -> BigIdeaState:
        request = state["request"]
        inspirations = deps.knowledge_base.retrieve(
            f"{request.positioning_statement} {request.benefit}",
            top_k=5,
        )
        return {"inspirations": inspirations}

    def generate_big_ideas(state: BigIdeaState) -> BigIdeaState:
        request = state["request"]
        inspirations = state.get("inspirations", [])
        prompt = deps.pipeline.prompt_builder.build(request, inspirations)
        headlines = deps.generator.generate(prompt, count=3)
        return {"prompt": prompt, "generated_headlines": headlines}

    def clarity_check(state: BigIdeaState) -> BigIdeaState:
        headlines = state.get("generated_headlines", [])
        clarity_scores = [deps.clarity.evaluate(headline) for headline in headlines]
        return {"clarity": clarity_scores}

    def design_mockup(state: BigIdeaState) -> BigIdeaState:
        request = state["request"]
        headlines = state.get("generated_headlines", [])
        mockups = [deps.mockups.generate(headline, request) for headline in headlines]
        return {"mockups": mockups}

    def claim_validation(state: BigIdeaState) -> BigIdeaState:
        request = state["request"]
        headlines = state.get("generated_headlines", [])
        claim_reviews = [deps.claims.validate(headline, request.benchmarks) for headline in headlines]
        return {"claim_reviews": claim_reviews}

    def output_dashboard(state: BigIdeaState) -> BigIdeaState:
        request = state["request"]
        headlines = state.get("generated_headlines", [])
        clarity = state.get("clarity", [])
        mockups = state.get("mockups", [])
        claim_reviews = state.get("claim_reviews", [])

        assembled: List[Dict[str, Any]] = []
        for idx, headline in enumerate(headlines):
            assembled.append(
                {
                    "headline": headline,
                    "clarity": clarity[idx] if idx < len(clarity) else {},
                    "mockup": mockups[idx] if idx < len(mockups) else {},
                    "claim_validation": claim_reviews[idx] if idx < len(claim_reviews) else {},
                }
            )

        dashboard = {
            "brand": request.brand,
            "positioning": request.positioning_statement,
            "inspirations": state.get("inspirations", []),
            "headlines": assembled,
        }
        return {"assembled_headlines": assembled, "dashboard": dashboard}

    graph.add_node("prepare_request", _ensure_request, retry=RetryPolicy(max_attempts=2))
    graph.add_node("retrieve_examples", retrieve_examples, retry=RetryPolicy(max_attempts=3))
    graph.add_node("generate_big_ideas", generate_big_ideas, retry=RetryPolicy(max_attempts=2))
    graph.add_node("clarity_check", clarity_check)
    graph.add_node("design_mockup", design_mockup)
    graph.add_node("claim_validation", claim_validation)
    graph.add_node("output_dashboard", output_dashboard)

    graph.add_edge(START, "prepare_request")
    graph.add_edge("prepare_request", "retrieve_examples")
    graph.add_edge("retrieve_examples", "generate_big_ideas")
    graph.add_edge("generate_big_ideas", "clarity_check")
    graph.add_edge("generate_big_ideas", "design_mockup")
    graph.add_edge("generate_big_ideas", "claim_validation")
    graph.add_edge("clarity_check", "output_dashboard")
    graph.add_edge("design_mockup", "output_dashboard")
    graph.add_edge("claim_validation", "output_dashboard")
    graph.add_edge("output_dashboard", END)

    return graph


def compile_big_idea_graph(*, dependencies: Optional[BigIdeaDependencies] = None) -> CompiledGraph:
    graph = build_big_idea_graph(dependencies=dependencies)
    return graph.compile()


__all__ = [
    "BigIdeaState",
    "BigIdeaDependencies",
    "build_big_idea_graph",
    "compile_big_idea_graph",
]
