from __future__ import annotations

import abc
from typing import Any, Dict, Iterable, List, Optional, Protocol


class StructuredLoggable(Protocol):
    """Protocol for types that emit structured log dictionaries."""

    def to_log(self) -> Dict[str, Any]:
        ...


class PageFetcher(abc.ABC):
    """Abstract interface for retrieving HTML documents."""

    @abc.abstractmethod
    async def fetch(self, url: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return dict containing url, status, headers, and html."""


class HTMLParser(abc.ABC):
    """Parses HTML into structured data for downstream pipelines."""

    @abc.abstractmethod
    def parse(self, html: str, *, url: Optional[str] = None) -> Dict[str, Any]:
        ...


class NLPAnalyzer(abc.ABC):
    """Runs language analytics over text documents."""

    @abc.abstractmethod
    def analyze(self, texts: Iterable[str], *, metadata: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        ...


class StorageAdapter(abc.ABC):
    """Persists and retrieves research artefacts."""

    @abc.abstractmethod
    def put(self, key: str, value: Dict[str, Any], *, ttl: Optional[int] = None) -> None:
        ...

    @abc.abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...


class VectorIndexAdapter(abc.ABC):
    """Embeds and indexes documents for semantic retrieval."""

    @abc.abstractmethod
    def upsert(self, documents: List[Dict[str, Any]]) -> None:
        ...

    @abc.abstractmethod
    def query(self, query_text: str, *, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...


class ConfigProvider(abc.ABC):
    """Supplies configuration dictionaries for the agent."""

    @abc.abstractmethod
    def get(self) -> Dict[str, Any]:
        ...


class PositionScoringModule(abc.ABC):
    """Scores messaging statements for a single framework dimension."""

    name: str

    @abc.abstractmethod
    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...
