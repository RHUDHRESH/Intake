"""Configuration management agent."""
from typing import Any, Dict, Mapping

from utils.base_agent import BaseAgent
from .tools import fetch_secret, get_config, set_config


class ConfigAgent(BaseAgent):
    """Expose configuration retrieval, storage, and secret fetching."""

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(input_data, Mapping):
            return {"error": "input_data must be a mapping"}

        action = input_data.get("action", "get").lower()
        key = input_data.get("key")
        value = input_data.get("value")
        source = input_data.get("source", "env")

        if action == "get" and key:
            return await get_config(key, source)
        if action == "set" and key is not None and value is not None:
            return await set_config(key, value, source)
        if action == "secret" and key:
            return await fetch_secret(key)

        return {"error": "Invalid config action or missing parameters"}

    def get_dependencies(self):
        return []
