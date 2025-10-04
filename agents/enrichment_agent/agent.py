"""Enrichment agent that augments records with external or computed data."""
from typing import Any, Dict, Mapping, Tuple

from utils.base_agent import AgentInput, BaseAgent
from .tools import enrich_custom, enrich_with_geo, enrich_with_ml, enrich_with_social


class EnrichmentAgent(BaseAgent):
    """Coordinate geo, social, ML, or custom enrichment workflows."""

    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        input_data = agent_input.input_data
        if not isinstance(input_data, Mapping):
            return {"error": "input_data must be a mapping"}

        action = (input_data.get("action") or self.config.get("default_action", "geo")).lower()
        data = input_data.get("data")
        params = input_data.get("params", {})

        if action == "geo":
            return await enrich_with_geo(
                data=data,
                address_field=params.get("address_field", "address"),
                api_key=params.get("api_key"),
                rate_limit_ms=params.get("rate_limit_ms", self.config.get("rate_limit_ms")),
            )
        if action == "social":
            return await enrich_with_social(
                data=data,
                handle_field=params.get("handle_field", "handle"),
                lookup=params.get("lookup"),
            )
        if action == "ml":
            return await enrich_with_ml(
                data=data,
                model=params.get("model", self.config.get("default_model", "default")),
                inference_fn=params.get("inference_fn"),
            )
        if action == "custom":
            return await enrich_custom(
                data=data,
                enrich_func=params.get("enrich_func"),
            )

        return {"error": f"Unknown enrichment action '{action}'"}

    def get_dependencies(self) -> Tuple[str, ...]:
        return tuple()
