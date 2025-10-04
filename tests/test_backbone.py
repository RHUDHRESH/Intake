"""Tests for the shared agent backbone."""
from typing import Any, Dict

import pytest

from core import (
    AgentContext,
    AgentContextManager,
    HITL_APPROVED,
    HITLRequest,
    InMemoryHITLQueue,
    RetryPolicy,
    TelemetryClient,
    TelemetryEvent,
    current_agent_context,
)
from core.errors import HumanInputRequiredError, RetryableAgentError
from utils.base_agent import AgentInput, BaseAgent


class StubTelemetry(TelemetryClient):
    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []
        self.exceptions: list[Any] = []

    def emit_event(self, event: TelemetryEvent) -> None:
        self.events.append(event)

    def emit_metric(self, name: str, value: float, *, attributes=None) -> None:
        return

    def capture_exception(self, error: BaseException, *, attributes=None) -> None:
        self.exceptions.append((error, attributes))


class DummyAgent(BaseAgent):
    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        mode = agent_input.input_data.get("mode")
        attempt = agent_input.metadata.get("attempt", 1)
        if mode == "retry" and attempt < 2:
            agent_input.metadata["attempt"] = attempt + 1
            raise RetryableAgentError("transient")
        if mode == "hitl":
            raise HumanInputRequiredError("manual approval needed")
        return {"echo": dict(agent_input.input_data)}

    def get_dependencies(self):
        return tuple()


def test_agent_input_coerce_generates_request_id():
    payload = {"foo": "bar"}
    input_obj = AgentInput.coerce(payload)
    assert input_obj.request_id
    assert input_obj.input_data == payload


def test_agent_context_manager_binds_context():
    context = AgentContext(request_id="abc123", session_id="sess")
    assert current_agent_context() is None
    with AgentContextManager(context):
        assert current_agent_context() == context
    assert current_agent_context() is None


@pytest.mark.asyncio
async def test_agent_execute_retries_and_emits_events():
    telemetry = StubTelemetry()
    agent = DummyAgent(
        {},
        telemetry_client=telemetry,
        retry_policy=RetryPolicy(attempts=2, base_delay=0.0),
    )
    agent_input = AgentInput(
        request_id="req-1",
        input_data={"mode": "retry"},
        metadata={"attempt": 1},
    )

    result = await agent.execute(agent_input)

    assert result["echo"]["mode"] == "retry"
    event_names = [event.name for event in telemetry.events]
    assert event_names.count("agent.start") == 1
    assert event_names.count("agent.success") == 1


@pytest.mark.asyncio
async def test_agent_hitl_enqueues_requests():
    queue = InMemoryHITLQueue()
    agent = DummyAgent({}, hitl_queue=queue)
    agent_input = AgentInput(request_id="req-hitl", input_data={"mode": "hitl"})

    with pytest.raises(HumanInputRequiredError):
        await agent.execute(agent_input)

    stored = await queue.get("req-hitl")
    assert stored is not None
    assert stored.status == "pending"


@pytest.mark.asyncio
async def test_hitl_queue_resolution():
    queue = InMemoryHITLQueue()
    context = AgentContext(request_id="req-2")
    request = await queue.submit(
        HITLRequest(
            request_id="req-2",
            task_name="dummy",
            payload={"foo": "bar"},
            context=context,
        )
    )
    assert request.status == "pending"

    await queue.resolve("req-2", HITL_APPROVED, {"note": "done"})
    resolved = await queue.get("req-2")
    assert resolved is not None
    assert resolved.status == HITL_APPROVED
    assert resolved.resolution == {"note": "done"}
    assert resolved.resolved_at is not None
