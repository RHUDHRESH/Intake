"""Core agent abstractions leveraging the shared backbone."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union
from uuid import uuid4

from core import (
    AgentContext,
    AgentContextManager,
    BaseHITLQueue,
    ConfigurableMixin,
    ContextualMixin,
    LoggingTelemetryClient,
    TelemetryClient,
    TelemetryMixin,
    RetryPolicy,
    coerce_agent_error,
)
from core.errors import HumanInputRequiredError
from core.hitl import HITLRequest, HITL_PENDING
from core.retry import retry_async


@dataclass
class AgentInput:
    """Normalized payload an agent consumes."""

    request_id: str
    input_data: Mapping[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Optional[AgentContext] = None

    def ensure_context(self) -> AgentContext:
        if self.context is None:
            self.context = AgentContext(
                request_id=self.request_id,
                session_id=self.session_id,
                user_id=self.user_id,
                metadata=dict(self.metadata),
            )
        return self.context

    @classmethod
    def coerce(cls, payload: Union["AgentInput", Mapping[str, Any]]) -> "AgentInput":
        if isinstance(payload, AgentInput):
            return payload
        if not isinstance(payload, Mapping):
            raise TypeError("AgentInput payload must be a mapping or AgentInput instance")
        request_id = str(payload.get("request_id") or payload.get("id") or uuid4())
        body = payload.get("input_data")
        if body is None:
            body = {k: v for k, v in payload.items() if k not in {"request_id", "id", "user_id", "session_id", "metadata", "context"}}
        if not isinstance(body, Mapping):
            raise ValueError("AgentInput payload must contain a mapping of inputs")
        metadata = payload.get("metadata") or {}
        if not isinstance(metadata, Mapping):
            raise ValueError("AgentInput metadata must be a mapping if provided")
        context = payload.get("context")
        if context is not None and not isinstance(context, AgentContext):
            raise TypeError("context must be an AgentContext instance")
        return cls(
            request_id=request_id,
            input_data=dict(body),
            user_id=payload.get("user_id"),
            session_id=payload.get("session_id"),
            metadata=dict(metadata),
            context=context,
        )


class BaseAgent(ConfigurableMixin, ContextualMixin, TelemetryMixin, ABC):
    """Shared behaviour for all domain agents."""

    agent_name: str = "BaseAgent"

    def __init__(
        self,
        config: Optional[Mapping[str, Any]] = None,
        *,
        telemetry_client: Optional[TelemetryClient] = None,
        retry_policy: Optional[RetryPolicy] = None,
        hitl_queue: Optional[BaseHITLQueue] = None,
    ) -> None:
        ConfigurableMixin.__init__(self, config)
        ContextualMixin.__init__(self)
        TelemetryMixin.__init__(self, telemetry_client or LoggingTelemetryClient())
        self.agent_name = getattr(self, "agent_name", self.__class__.__name__)
        self.retry_policy = retry_policy or RetryPolicy()
        self.hitl_queue = hitl_queue

    async def execute(self, input_payload: Union[AgentInput, Mapping[str, Any]]) -> Dict[str, Any]:
        """Entry point invoked by orchestrators or routers."""

        agent_input = AgentInput.coerce(input_payload)
        context = agent_input.ensure_context()
        async with AgentContextManager(context):
            self.emit_event(
                "agent.start",
                agent=self.agent_name,
                request_id=agent_input.request_id,
            )
            try:
                return await self._execute_with_retry(agent_input)
            except HumanInputRequiredError as hitl_err:
                await self._enqueue_hitl(agent_input, hitl_err)
                self.capture_exception(hitl_err, agent=self.agent_name)
                raise
            except Exception as raw_exc:  # noqa: BLE001
                agent_error = coerce_agent_error(raw_exc)
                self.capture_exception(agent_error, agent=self.agent_name)
                raise agent_error

    async def _execute_with_retry(self, agent_input: AgentInput) -> Dict[str, Any]:
        async def runner(payload: AgentInput) -> Dict[str, Any]:
            result = await self.run(payload)
            self.emit_event(
                "agent.success",
                agent=self.agent_name,
                request_id=payload.request_id,
            )
            return result

        return await retry_async(runner, agent_input, policy=self.retry_policy)

    async def _enqueue_hitl(self, agent_input: AgentInput, error: HumanInputRequiredError) -> None:
        if self.hitl_queue is None:
            return
        request = HITLRequest(
            request_id=agent_input.request_id,
            task_name=self.agent_name,
            payload={
                "input": dict(agent_input.input_data),
                "metadata": dict(agent_input.metadata),
                "error": error.to_dict() if hasattr(error, "to_dict") else str(error),
            },
            context=agent_input.context,
        )
        await self.hitl_queue.submit(request)
        self.emit_event(
            "agent.hitl_enqueued",
            agent=self.agent_name,
            request_id=agent_input.request_id,
            status=HITL_PENDING,
        )

    @abstractmethod
    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        """Subclasses implement their business logic here."""

    @abstractmethod
    def get_dependencies(self) -> Tuple[str, ...]:
        """Return labels for downstream dependencies."""

    def requires_web_scraping(self) -> bool:
        return self.get_flag("requires_web_scraping", False)
