"""Telemetry primitives for agents and tools."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

import structlog

from .context import AgentContext, current_agent_context


@dataclass
class TelemetryEvent:
    """Structured payload emitted by the telemetry layer."""

    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    context: Optional[AgentContext] = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TelemetryClient(ABC):
    """Abstract telemetry transport."""

    @abstractmethod
    def emit_event(self, event: TelemetryEvent) -> None:
        """Send an application event."""

    def emit_metric(self, name: str, value: float, *, attributes: Optional[Mapping[str, Any]] = None) -> None:
        """Send a numeric observation."""

    def capture_exception(self, error: BaseException, *, attributes: Optional[Mapping[str, Any]] = None) -> None:
        """Record an exception with optional metadata."""


class LoggingTelemetryClient(TelemetryClient):
    """Default telemetry client that logs via :mod:`structlog`."""

    def __init__(self, logger: Optional[structlog.BoundLogger] = None) -> None:
        self._logger = logger or structlog.get_logger("telemetry")

    def emit_event(self, event: TelemetryEvent) -> None:
        payload = dict(event.attributes)
        payload.setdefault("timestamp", event.timestamp.isoformat())
        if event.context:
            payload.setdefault("request_id", event.context.request_id)
            if event.context.session_id:
                payload.setdefault("session_id", event.context.session_id)
            if event.context.span_id:
                payload.setdefault("span_id", event.context.span_id)
        self._logger.info(event.name, **payload)

    def emit_metric(self, name: str, value: float, *, attributes: Optional[Mapping[str, Any]] = None) -> None:
        payload = {"value": value}
        if attributes:
            payload.update(attributes)
        self._logger.info(f"metric.{name}", **payload)

    def capture_exception(self, error: BaseException, *, attributes: Optional[Mapping[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {"error": repr(error)}
        if attributes:
            payload.update(attributes)
        self._logger.error("exception", **payload)


class NullTelemetryClient(TelemetryClient):
    """Telemetry sink that drops all events."""

    def emit_event(self, event: TelemetryEvent) -> None:  # pragma: no cover - intentional no-op
        return

    def emit_metric(self, name: str, value: float, *, attributes: Optional[Mapping[str, Any]] = None) -> None:  # pragma: no cover - intentional no-op
        return

    def capture_exception(self, error: BaseException, *, attributes: Optional[Mapping[str, Any]] = None) -> None:  # pragma: no cover - intentional no-op
        return


class TelemetryMixin:
    """Mixin that wires telemetry into agents and tools."""

    def __init__(self, telemetry_client: Optional[TelemetryClient] = None) -> None:
        self._telemetry_client = telemetry_client or LoggingTelemetryClient()

    @property
    def telemetry(self) -> TelemetryClient:
        return self._telemetry_client

    def emit_event(self, name: str, **attributes: Any) -> None:
        context = attributes.pop("context", None) or current_agent_context()
        event = TelemetryEvent(name=name, attributes=attributes, context=context)
        self.telemetry.emit_event(event)

    def emit_metric(self, name: str, value: float, **attributes: Any) -> None:
        self.telemetry.emit_metric(name, value, attributes=attributes or None)

    def capture_exception(self, error: BaseException, **attributes: Any) -> None:
        self.telemetry.capture_exception(error, attributes=attributes or None)
