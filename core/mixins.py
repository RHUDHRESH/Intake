"""Reusable mixins for agents and tools."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional

from .context import AgentContext, AgentContextManager, current_agent_context
from .telemetry import TelemetryMixin


class ConfigurableMixin:
    """Provide typed helpers around configuration dictionaries."""

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        self._config: Dict[str, Any] = dict(config or {})

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_config_value(self, key: str, default: Any = None, *, expected_type: Optional[type] = None) -> Any:
        value = self._config.get(key, default)
        if expected_type is not None and value is not None and not isinstance(value, expected_type):
            raise TypeError(f"Configuration value '{key}' expected type {expected_type.__name__}, got {type(value).__name__}")
        return value

    def get_flag(self, key: str, default: bool = False) -> bool:
        value = self._config.get(key, default)
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "on"}
        return bool(value)

    def set_config_value(self, key: str, value: Any) -> None:
        self._config[key] = value


class ContextualMixin:
    """Expose helpers for managing :class:`AgentContext` lifecycles."""

    def __init__(self, context: Optional[AgentContext] = None) -> None:
        self._bound_context = context

    @property
    def context(self) -> Optional[AgentContext]:
        return self._bound_context or current_agent_context()

    def bind_context(self, context: AgentContext) -> AgentContextManager:
        self._bound_context = context
        return AgentContextManager(context)

    def clear_bound_context(self) -> None:
        self._bound_context = None


class AgentToolkitMixin(TelemetryMixin, ConfigurableMixin, ContextualMixin):
    """Aggregate mixin for LangChain tools executing inside the agent framework."""

    def __init__(
        self,
        config: Optional[Mapping[str, Any]] = None,
        telemetry_client=None,
        context: Optional[AgentContext] = None,
    ) -> None:
        ConfigurableMixin.__init__(self, config)
        ContextualMixin.__init__(self, context)
        TelemetryMixin.__init__(self, telemetry_client)


__all__ = [
    "ConfigurableMixin",
    "ContextualMixin",
    "AgentToolkitMixin",
]
