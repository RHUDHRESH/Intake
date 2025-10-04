"""Transformation agent handling mapping, filtering, aggregation, and format conversion."""
from typing import Any, Dict, Mapping

from utils.base_agent import BaseAgent
from .tools import (
    aggregate_data,
    convert_format,
    custom_transform,
    filter_data,
    map_fields,
)


class TransformationAgent(BaseAgent):
    """Provide generalized data transformation operations."""

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(input_data, Mapping):
            return {"error": "input_data must be a mapping"}

        action = input_data.get("action") or self.config.get("default_action", "map")
        data = input_data.get("data")
        params = input_data.get("params", {})

        if action == "map":
            return await map_fields(
                data=data,
                mapping=params.get("mapping") or {},
            )
        if action == "filter":
            return await filter_data(
                data=data,
                condition=params.get("condition"),
            )
        if action == "aggregate":
            return await aggregate_data(
                data=data,
                agg_func=params.get("agg_func"),
                key=params.get("key"),
                group_by=params.get("group_by"),
            )
        if action == "convert":
            return await convert_format(
                data=data,
                to_format=params.get("to_format", "json"),
                root_name=params.get("root_name", "items"),
                item_name=params.get("item_name", "item"),
            )
        if action == "custom":
            return await custom_transform(
                data=data,
                transformer=params.get("transformer"),
            )

        return {"error": f"Unknown transformation action '{action}'"}

    def get_dependencies(self):
        return []
