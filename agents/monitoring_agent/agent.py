"""Monitoring agent for logging events, errors, and metrics."""
from typing import Any, Dict, Mapping

from utils.base_agent import BaseAgent
from .tools import fetch_logs, log_error, log_event, track_metric


class MonitoringAgent(BaseAgent):
    """Provide a consistent interface for monitoring-related actions."""

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action")
        if not action:
            return {"error": "action is required"}

        event = input_data.get("event")
        details = input_data.get("details", {})
        if not isinstance(details, Mapping):
            details = {"value": details}

        metric = input_data.get("metric")
        value = input_data.get("value")
        query = input_data.get("query", {})
        if not isinstance(query, Mapping):
            query = {}

        if action == "log_event" and event:
            return await log_event(event, details)
        if action == "log_error" and event:
            return await log_error(event, details)
        if action == "track_metric" and metric is not None and value is not None:
            return await track_metric(metric, value)
        if action == "fetch_logs":
            return await fetch_logs(query)

        return {"error": "Invalid monitoring action or missing parameters"}

    def get_dependencies(self):
        return []
