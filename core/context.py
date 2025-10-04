"""Execution context primitives shared across agents and tools."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_CURRENT_CONTEXT: ContextVar[Optional["AgentContext"]] = ContextVar(
    "agent_current_context",
    default=None,
)


@dataclass
class AgentContext:
    """Runtime metadata propagated between agents, tools, and telemetry."""

    request_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    span_id: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def child(self, **overrides: Any) -> "AgentContext":
        """Create a derived context for nested executions."""
        payload = {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "parent_span_id": self.span_id or self.parent_span_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "metadata": dict(self.metadata),
        }
        payload.update(overrides)
        return AgentContext(**payload)


class AgentContextManager:
    """Bind an :class:`AgentContext` to the current async task."""

    def __init__(self, context: AgentContext):
        self._context = context
        self._token = None

    def __enter__(self) -> AgentContext:
        self._token = _CURRENT_CONTEXT.set(self._context)
        return self._context

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            _CURRENT_CONTEXT.reset(self._token)
            self._token = None

    async def __aenter__(self) -> AgentContext:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.__exit__(exc_type, exc, tb)


def current_agent_context() -> Optional[AgentContext]:
    """Return the context bound to the current execution task, if any."""

    return _CURRENT_CONTEXT.get()


def bind_context(context: Optional[AgentContext]) -> Optional[AgentContext]:
    """Bind *context* to the current task and return the previous value."""

    previous = _CURRENT_CONTEXT.get()
    if context is None:
        _CURRENT_CONTEXT.set(None)
    else:
        _CURRENT_CONTEXT.set(context)
    return previous


def clear_context() -> None:
    """Detach any context associated with the current task."""

    _CURRENT_CONTEXT.set(None)
