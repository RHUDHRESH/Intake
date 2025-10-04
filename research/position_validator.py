from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from position_validator import (
    AdaptScoringModule,
    GodinScoringModule,
    OgilvyScoringModule,
    PositionValidatorEngine,
    Switch6ScoringModule,
)
from position_validator.engine import ModuleConfig


class PositionValidator:
    """Wrapper around PositionValidatorEngine with default scoring modules."""

    def __init__(
        self,
        modules: Optional[Iterable] = None,
        *,
        module_overrides: Optional[Dict[str, ModuleConfig]] = None,
    ) -> None:
        self._modules = list(modules) if modules else [
            AdaptScoringModule(),
            Switch6ScoringModule(),
            OgilvyScoringModule(),
            GodinScoringModule(),
        ]
        self._engine = PositionValidatorEngine(self._modules)
        self._overrides = module_overrides or {}

    def validate(
        self,
        data: Dict[str, Any],
        *,
        module_overrides: Optional[Dict[str, ModuleConfig]] = None,
    ) -> Dict[str, Any]:
        statement = data.get("position_statement", "").strip()
        context = {
            "user_type": data.get("user_type"),
            "what_you_do": data.get("what_you_do"),
            "main_challenge": data.get("main_challenge"),
        }
        overrides = module_overrides or self._overrides
        result = self._engine.score(statement, context=context, module_overrides=overrides)
        module_scores = {
            module_result["module"]: module_result.get("score", 0.0)
            for module_result in result.get("module_results", [])
        }
        return {
            "statement": statement,
            "scores": {
                "overall_strength": result.get("score", 0.0),
                "module_scores": module_scores,
            },
            "feedback": result.get("feedback", []),
        }


__all__ = ["PositionValidator"]
