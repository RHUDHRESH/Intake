"""Human-in-the-loop (HITL) queue interfaces."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .context import AgentContext


HITL_PENDING = "pending"
HITL_APPROVED = "approved"
HITL_REJECTED = "rejected"
HITL_CANCELLED = "cancelled"


@dataclass
class HITLRequest:
    request_id: str
    task_name: str
    payload: Dict[str, Any]
    context: Optional[AgentContext] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    status: str = HITL_PENDING
    resolution: Optional[Dict[str, Any]] = None

    def mark(self, status: str, resolution: Optional[Dict[str, Any]] = None) -> None:
        self.status = status
        self.resolution = resolution
        self.resolved_at = datetime.now(timezone.utc)


class BaseHITLQueue(ABC):
    """Abstract interface for queueing human review tasks."""

    @abstractmethod
    async def submit(self, request: HITLRequest) -> HITLRequest:
        """Add a new HITL request."""

    @abstractmethod
    async def resolve(self, request_id: str, status: str, resolution: Optional[Dict[str, Any]] = None) -> None:
        """Resolve a pending request."""

    @abstractmethod
    async def get(self, request_id: str) -> Optional[HITLRequest]:
        """Fetch a request by identifier."""


class InMemoryHITLQueue(BaseHITLQueue):
    """Simple in-memory implementation suitable for unit tests."""

    def __init__(self) -> None:
        self._requests: Dict[str, HITLRequest] = {}
        self._lock = asyncio.Lock()

    async def submit(self, request: HITLRequest) -> HITLRequest:
        async with self._lock:
            self._requests[request.request_id] = request
        return request

    async def resolve(self, request_id: str, status: str, resolution: Optional[Dict[str, Any]] = None) -> None:
        async with self._lock:
            item = self._requests.get(request_id)
            if item is None:
                raise KeyError(f"Unknown HITL request '{request_id}'")
            item.mark(status, resolution)

    async def get(self, request_id: str) -> Optional[HITLRequest]:
        async with self._lock:
            return self._requests.get(request_id)
