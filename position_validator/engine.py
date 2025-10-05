from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from market_research.interfaces import PositionScoringModule


@dataclass
class ModuleConfig:
    name: str
    weight: float = 1.0
    enabled: bool = True


class PositionValidatorEngine:
    """Runs pluggable scoring modules over positioning statements."""

    def __init__(self, modules: Iterable[PositionScoringModule]) -> None:
        self._modules = {module.name: module for module in modules}

    def score(
        self,
        statement: str,
        *,
        context: Optional[Dict[str, str]] = None,
        module_overrides: Optional[Dict[str, ModuleConfig]] = None,
    ) -> Dict[str, Any]:
        context = context or {}
        overrides = module_overrides or {}
        results: List[Dict[str, Any]] = []
        total_weight = 0.0
        weighted_score = 0.0

        for name, module in self._modules.items():
            cfg = overrides.get(name, ModuleConfig(name=name))
            if not cfg.enabled:
                continue
            result = module.score(statement, context=context)
            weight = cfg.weight if cfg.weight else result.get("weight", 1.0)
            result["weight"] = weight
            results.append(result)
            total_weight += weight
            weighted_score += result.get("score", 0.0) * weight

        aggregate = weighted_score / total_weight if total_weight else 0.0
        feedback = _flatten_feedback(results)
        return {
            "statement": statement,
            "score": round(aggregate, 3),
            "module_results": results,
            "feedback": feedback,
        }


def _flatten_feedback(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for result in results:
        module = result.get("module")
        for entry in result.get("feedback", []) or []:
            payload = dict(entry)
            payload["module"] = module
            flattened.append(payload)
    return flattened


__all__ = ["ModuleConfig", "PositionValidatorEngine"]
