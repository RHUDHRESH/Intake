"""Scheduler Agent for calendar events and background jobs."""
from typing import Any, Dict, Tuple

from utils.base_agent import AgentInput, BaseAgent
from .tools import (
    create_calendar_event,
    create_cloud_job,
    delete_calendar_event,
    update_calendar_event,
)


class SchedulerAgent(BaseAgent):
    """Manage calendar events and scheduler jobs."""

    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        input_data = agent_input.input_data
        action = input_data.get("action", self.config.get("default_action", "create_event"))
        event_data = input_data.get("event_data") or {}
        job_data = input_data.get("job_data") or {}
        event_id = input_data.get("event_id")

        if action == "create_event" and event_data:
            return await create_calendar_event(event_data)
        if action == "update_event" and event_id and event_data:
            return await update_calendar_event(event_id, event_data)
        if action == "delete_event" and event_id:
            return await delete_calendar_event(event_id)
        if action == "create_job" and job_data:
            return await create_cloud_job(job_data)

        return {"error": "Invalid action or missing parameters"}

    def get_dependencies(self) -> Tuple[str, ...]:
        return tuple()
