"""Validation agent for enforcing data quality rules."""
from typing import Any, Dict, Mapping, Sequence

from utils.base_agent import BaseAgent
from .tools import run_validation_suite


class ValidationAgent(BaseAgent):
    """Run schema, required, type, constraint, and custom validations."""

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(input_data, Mapping):
            return {"error": "input_data must be a mapping"}

        defaults = {
            "default_type": input_data.get("default_type") or self.config.get("default_type", "schema"),
            "jsonschema_draft": input_data.get("jsonschema_draft") or self.config.get("jsonschema_draft", "draft7"),
            "allow_empty_strings": input_data.get("allow_empty_strings", self.config.get("allow_empty_strings", False)),
            "stop_on_failure": input_data.get("stop_on_failure", self.config.get("stop_on_failure", False)),
            "custom_registry": input_data.get("custom_registry") or self.config.get("custom_registry"),
        }

        checks: Sequence[Mapping[str, Any]]
        base_data = input_data.get("data", {})
        if "checks" in input_data:
            raw_checks = input_data.get("checks") or []
            prepared = []
            for check in raw_checks:
                if not isinstance(check, Mapping):
                    continue
                merged = dict(check)
                merged.setdefault("data", base_data)
                prepared.append(merged)
            checks = prepared
        else:
            check_type = input_data.get("type") or defaults["default_type"]
            single_check = {
                "type": check_type,
                "data": base_data,
                "schema": input_data.get("schema"),
                "required": input_data.get("required"),
                "rules": input_data.get("rules"),
                "constraints": input_data.get("constraints"),
                "type_rules": input_data.get("type_rules") or input_data.get("types"),
                "label": input_data.get("label"),
                "allow_empty": input_data.get("allow_empty"),
                "skip_missing": input_data.get("skip_missing"),
                "delimiter": input_data.get("delimiter"),
            }
            checks = [single_check]

        suite_result = await run_validation_suite(checks, defaults)
        if len(suite_result.get("results", [])) == 1:
            result = suite_result["results"][0]
            result["overall_valid"] = suite_result["valid"]
            return result
        return suite_result

    def get_dependencies(self):
        return []
