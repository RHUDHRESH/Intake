from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from .interfaces import NLPAnalyzer


try:  # pragma: no cover - optional heavy deps
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


try:  # pragma: no cover - optional clustering libs
    import hdbscan
    import umap
except Exception:  # pragma: no cover
    hdbscan = None  # type: ignore
    umap = None  # type: ignore


@dataclass
class AnalyzerResult:
    embeddings: List[List[float]]
    clusters: List[Dict[str, Any]]
    metadata: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embeddings": self.embeddings,
            "clusters": self.clusters,
            "metadata": self.metadata,
        }


class EmbeddingNLPAnalyzer(NLPAnalyzer):
    """Embeds text, performs optional clustering, returns structured payload."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name) if SentenceTransformer else None

    def analyze(
        self,
        texts: Iterable[str],
        *,
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        docs = list(texts)
        if not docs:
            return AnalyzerResult([], [], metadata or []).to_dict()

        embeddings = self._embed(docs)
        clusters = self._cluster(embeddings, docs, metadata or [])
        return AnalyzerResult(embeddings, clusters, metadata or []).to_dict()

    def _embed(self, docs: List[str]) -> List[List[float]]:
        if self._model is None:
            return [[float(len(doc) % 10)] * 4 for doc in docs]
        vectors = self._model.encode(docs, normalize_embeddings=True)
        return vectors.tolist()

    def _cluster(
        self,
        embeddings: List[List[float]],
        docs: List[str],
        metadata: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not embeddings:
            return []
        matrix = np.array(embeddings)
        labels = self._run_hdbscan(matrix) if hdbscan and umap else self._run_simple_threshold(matrix)
        clusters: Dict[int, Dict[str, Any]] = {}
        for idx, label in enumerate(labels):
            key = int(label)
            cluster = clusters.setdefault(
                key,
                {
                    "id": key,
                    "documents": [],
                    "metadata": [],
                },
            )
            cluster["documents"].append(docs[idx])
            if idx < len(metadata):
                cluster["metadata"].append(metadata[idx])
        return list(clusters.values())

    def _run_hdbscan(self, matrix: np.ndarray) -> List[int]:  # pragma: no cover - heavy path
        reducer = umap.UMAP(min_dist=0.25, n_neighbors=10)
        reduced = reducer.fit_transform(matrix)
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2)
        return clusterer.fit_predict(reduced).tolist()

    def _run_simple_threshold(self, matrix: np.ndarray) -> List[int]:
        labels = []
        base = matrix.mean(axis=1)
        for value in base:
            labels.append(1 if value > np.mean(base) else 0)
        return labels


__all__ = ["EmbeddingNLPAnalyzer"]
