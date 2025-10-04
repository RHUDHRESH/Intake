from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional vector backend
    import chromadb
    from chromadb.config import Settings
except Exception:  # pragma: no cover
    chromadb = None  # type: ignore
    Settings = None  # type: ignore

from .interfaces import StorageAdapter, VectorIndexAdapter


class InMemoryStorageAdapter(StorageAdapter):
    """Thread-safe in-memory storage with TTL support."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def put(self, key: str, value: Dict[str, Any], *, ttl: Optional[int] = None) -> None:
        expiry = time.time() + ttl if ttl else None
        self._store[key] = {"value": value, "expiry": expiry}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        payload = self._store.get(key)
        if not payload:
            return None
        expiry = payload.get("expiry")
        if expiry and expiry < time.time():
            self._store.pop(key, None)
            return None
        return dict(payload["value"])


class JSONFileStorageAdapter(StorageAdapter):
    """Persists documents to disk, primarily for caching raw HTML."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, value: Dict[str, Any], *, ttl: Optional[int] = None) -> None:
        payload = {"value": value, "expiry": time.time() + ttl if ttl else None}
        path = self._root / f"{self._safe_key(key)}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._root / f"{self._safe_key(key)}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        expiry = payload.get("expiry")
        if expiry and expiry < time.time():
            path.unlink(missing_ok=True)
            return None
        return dict(payload.get("value", {}))

    def _safe_key(self, key: str) -> str:
        return key.replace(":", "_").replace("/", "_")


class ChromaVectorIndexAdapter(VectorIndexAdapter):
    """ChromaDB-backed vector index with metadata-rich documents."""

    def __init__(self, collection: str = "market_research", persist_dir: Optional[Path] = None) -> None:
        if chromadb is None or Settings is None:  # pragma: no cover - optional path
            raise ImportError("chromadb is required for ChromaVectorIndexAdapter")
        persist_dir = persist_dir or Path("data/chroma_market")
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.Client(
            Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(persist_dir))
        )
        self._collection = self._client.get_or_create_collection(collection)

    def upsert(self, documents: List[Dict[str, Any]]) -> None:
        if not documents:
            return
        ids = [doc.get("id") or doc.get("url") or str(time.time_ns() + idx) for idx, doc in enumerate(documents)]
        embeddings = [doc.get("embedding") for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        texts = [doc.get("text", "") for doc in documents]
        self._collection.upsert(ids=ids, documents=texts, embeddings=embeddings or None, metadatas=metadatas)

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        raw = self._collection.query(query_texts=[query_text], n_results=top_k, where=filters)
        results: List[Dict[str, Any]] = []
        for idx, doc_id in enumerate(raw.get("ids", [[]])[0]):
            results.append(
                {
                    "id": doc_id,
                    "metadata": raw.get("metadatas", [[]])[0][idx],
                    "text": raw.get("documents", [[]])[0][idx],
                    "distance": raw.get("distances", [[]])[0][idx],
                }
            )
        return results


__all__ = [
    "ChromaVectorIndexAdapter",
    "InMemoryStorageAdapter",
    "JSONFileStorageAdapter",
]
