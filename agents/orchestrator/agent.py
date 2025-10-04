"""Orchestrator agent coordinating workflow execution."""
import asyncio
from typing import Any, Dict, Iterable, List, Mapping, Type

from utils.base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """Coordinate agent execution sequentially or in parallel."""

    def __init__(self, config: Mapping[str, Any], agent_registry: Mapping[str, Type[BaseAgent]]):
        if not isinstance(agent_registry, Mapping):
            raise TypeError("agent_registry must be a mapping of labels to agent classes")
        super().__init__(dict(config))
        self.agent_registry: Dict[str, Type[BaseAgent]] = dict(agent_registry)
        self.available_agents: Dict[str, Type[BaseAgent]] = dict(agent_registry)

    def get_dependencies(self) -> List[str]:
        return [
            "web_crawler",
            "social_agent",
            "nlp_agent",
            "map_agent",
            "review_agent",
            "doc_agent",
            "database_agent",
            "scheduler_agent",
            "notification_agent",
            "analytics_agent",
            "export_agent",
        ]

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(input_data, Mapping):
            raise TypeError("input_data must be a mapping with workflow instructions")

        workflow = list(input_data.get("workflow", []))
        parallel = bool(input_data.get("parallel", False))

        if not workflow:
            return {"workflow_results": []}

        if parallel:
            results = await self._run_parallel(workflow)
        else:
            results = await self._run_sequential(workflow)

        return {
            "workflow_results": results,
            "parallel": parallel,
        }

    async def _run_sequential(self, steps: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for step in steps:
            label, params = self._extract_step(step)
            outcome = await self._invoke_agent(label, params)
            results.append(outcome)
            if outcome.get("error"):
                break
        return results

    async def _run_parallel(self, steps: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        coroutines = []
        for step in steps:
            label, params = self._extract_step(step)
            coroutines.append(self._invoke_agent(label, params))
        return await asyncio.gather(*coroutines)

    def _extract_step(self, step: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
        if not isinstance(step, Mapping):
            raise TypeError("Each workflow step must be a mapping with an 'agent' key")
        label = step.get("agent")
        if not label:
            raise ValueError("Workflow step missing required 'agent' label")
        params = step.get("params") or {}
        if not isinstance(params, Mapping):
            raise TypeError("Workflow step 'params' must be a mapping")
        return label, dict(params)

    async def _invoke_agent(self, label: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        agent_cls = self.agent_registry.get(label)
        if agent_cls is None:
            return {
                "agent": label,
                "error": f"Agent '{label}' is not registered",
            }

        agent_config = self._resolve_agent_config(label)
        agent_instance: BaseAgent = agent_cls(agent_config)

        try:
            output = await agent_instance.execute(dict(params))
            return {"agent": label, "output": output}
        except Exception as exc:  # pragma: no cover - defensive wrapper
            return {
                "agent": label,
                "error": str(exc),
            }

    def _resolve_agent_config(self, label: str) -> Mapping[str, Any]:
        overrides = self.config.get("agents")
        if isinstance(overrides, Mapping) and label in overrides:
            candidate = overrides[label]
            if isinstance(candidate, Mapping):
                return dict(candidate)
        label_config = self.config.get(label)
        if isinstance(label_config, Mapping):
            return dict(label_config)
        return dict(self.config)

    def register_agent(self, label: str, agent_cls: Type[BaseAgent]) -> None:
        if not label or not isinstance(label, str):
            raise ValueError("label must be a non-empty string")
        if not callable(agent_cls):
            raise TypeError("agent_cls must be a callable agent class")
        self.agent_registry[label] = agent_cls
        self.available_agents[label] = agent_cls

    async def list_available_agents(self) -> Dict[str, Any]:
        return {label: cls.__name__ for label, cls in self.agent_registry.items()}

    async def get_workflow_status(self, request_id: str) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "status": "unknown",
            "detail": "Orchestrator does not persist workflow state by default.",
        }
