from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..interfaces import NLPAnalyzer, VectorIndexAdapter
from ..telemetry import emit_log


class AnalysisState(TypedDict, total=False):
    documents: List[Dict[str, Any]]
    analysis: Dict[str, Any]
    indexed: bool


def build_analysis_graph(
    *,
    analyzer: NLPAnalyzer,
    index: VectorIndexAdapter,
    batch_size: int = 8,
) -> StateGraph:
    graph = StateGraph(AnalysisState)

    def prepare_node(state: AnalysisState) -> AnalysisState:
        docs = state.get("documents", [])
        if not docs:
            emit_log("analysis.prepare.skipped", extra={"reason": "no_documents"})
            return {"documents": []}
        return {"documents": docs}

    def analyze_node(state: AnalysisState) -> AnalysisState:
        docs = state.get("documents", [])
        if not docs:
            return {"analysis": {"embeddings": [], "clusters": []}}
        texts = [doc.get("parsed", {}).get("text") or doc.get("html", "") for doc in docs]
        metadata = [_build_metadata(doc) for doc in docs]
        result = analyzer.analyze(texts, metadata=metadata)
        return {"analysis": result, "documents": docs}

    def index_node(state: AnalysisState) -> AnalysisState:
        docs = state.get("documents", [])
        analysis = state.get("analysis", {})
        embeddings = analysis.get("embeddings", [])
        if not docs or not embeddings:
            emit_log("analysis.index.skipped", extra={"reason": "empty_embeddings"})
            return {"indexed": False}
        batched = _batched_vectors(docs, embeddings)
        index.upsert(batched)
        return {"indexed": True}

    graph.add_node("prepare", prepare_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("index", index_node)

    graph.set_entry_point("prepare")
    graph.add_conditional_edges(
        "prepare",
        lambda state: "analyze" if state.get("documents") else END,
        {"analyze": "analyze", END: END},
    )
    graph.add_edge("analyze", "index")
    graph.add_edge("index", END)
    return graph


def _batched_vectors(docs: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for idx, doc in enumerate(docs):
        meta = _build_metadata(doc)
        output.append(
            {
                "id": doc.get("url") or doc.get("id") or str(idx),
                "text": doc.get("parsed", {}).get("text") or "",
                "embedding": embeddings[idx] if idx < len(embeddings) else [],
                "metadata": meta,
            }
        )
    return output


def _build_metadata(doc: Dict[str, Any]) -> Dict[str, Any]:
    parsed = doc.get("parsed", {})
    metadata = {
        "url": doc.get("url"),
        "title": parsed.get("title"),
        "description": parsed.get("description"),
        "industry": doc.get("metadata", {}).get("industry"),
        "fetched_at": doc.get("fetched_at"),
        "source": doc.get("source"),
    }
    return {k: v for k, v in metadata.items() if v is not None}


__all__ = ["AnalysisState", "build_analysis_graph"]
