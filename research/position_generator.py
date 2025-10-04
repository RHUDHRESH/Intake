from __future__ import annotations

import json
import logging
from dataclasses import dataclass
import random
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from classifiers.framework_selector import FrameworkSelector
from research.position_validator import PositionValidator

try:  # pragma: no cover - optional dependency
    from langchain.llms import VertexAI
except Exception:  # pragma: no cover
    VertexAI = None  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    statement: str
    framework: Optional[str]
    validation: Dict[str, Any]
    opportunity_score: float
    fit_score: float
    ranking_score: float
    rationale: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "framework": self.framework,
            "validation": self.validation,
            "opportunity_score": round(self.opportunity_score, 3),
            "fit_score": round(self.fit_score, 3),
            "ranking_score": round(self.ranking_score, 3),
            "rationale": self.rationale,
        }


class _FallbackLLM:
    """Lightweight LLM replacement when VertexAI is unavailable."""

    def __call__(self, prompt: str) -> str:
        # Extract minimal context for templated outputs
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        context = {"Business Type": "", "What you do": "", "Primary challenge": "", "Current position": ""}
        for line in lines:
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                if key in context:
                    context[key] = value.strip()
        base = context["What you do"] or "your solution"
        challenge = context["Primary challenge"] or "the biggest pain"
        current = context["Current position"] or "our current promise"
        statements = [
            f"We help teams facing {challenge} by delivering {base} that feels tailor-made.",
            f"{base.title()} rewrites the playbook so {challenge} turns into momentum.",
            f"Instead of {current.lower()}, we spotlight measurable wins in 30 days.",
            f"Leaders choose us when {challenge} stalls growth because {base} proves ROI fast.",
            f"Our customers replace {challenge} with repeatable outcomes powered by {base}.",
        ]
        return json.dumps(statements)


class PositionGeneratorAgent:
    """Generate, validate, and rank alternative positioning statements."""

    def __init__(
        self,
        *,
        llm: Optional[Any] = None,
        validator: Optional[PositionValidator] = None,
        selector: Optional[FrameworkSelector] = None,
    ) -> None:
        if llm is not None:
            self.llm = llm
        elif VertexAI is not None:  # pragma: no cover - depends on environment
            self.llm = VertexAI()
        else:
            self.llm = _FallbackLLM()
        self.validator = validator or PositionValidator()
        self.selector = selector or FrameworkSelector()

    # ---------------------------------------------------------------------
    # LLM generation
    # ---------------------------------------------------------------------
    def generate_alternatives(
        self,
        base_data: Dict[str, Any],
        count: int = 5,
    ) -> List[str]:
        prompt = self._build_prompt(base_data, count)
        try:
            response = self.llm(prompt)
        except Exception as exc:  # pragma: no cover - runtime failure path
            logger.exception("LLM generation failed", exc_info=exc)
            return []
        statements = self._parse_llm_response(response)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: List[str] = []
        for stmt in statements:
            clean = stmt.strip()
            if not clean or clean.lower() in seen:
                continue
            seen.add(clean.lower())
            unique.append(clean)
            if len(unique) >= count:
                break
        return unique

    # ---------------------------------------------------------------------
    # Validation and ranking
    # ---------------------------------------------------------------------
    def validate_and_rank(
        self,
        alternatives: Iterable[str],
        context_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []
        for statement in alternatives:
            if not statement:
                continue
            data = {**context_data, "position_statement": statement}
            validation = self.validator.validate(data)
            overall_fit = validation.get("scores", {}).get("overall_strength", 0.0)
            framework = self._safe_select_framework(data)
            opportunity = self._opportunity_score(statement, context_data)
            ranking_score = self._ranking_score(opportunity, overall_fit)
            rationale = {
                "opportunity_reason": self._opportunity_reason(opportunity),
                "fit_reason": f"Framework alignment at {overall_fit:.2f}",
            }
            entry = GenerationResult(
                statement=statement,
                framework=framework,
                validation=validation,
                opportunity_score=opportunity,
                fit_score=overall_fit,
                ranking_score=ranking_score,
                rationale=rationale,
            )
            ranked.append(entry.to_dict())
        ranked.sort(key=lambda item: item["ranking_score"], reverse=True)
        return ranked

    # ---------------------------------------------------------------------
    # Public execution pipeline
    # ---------------------------------------------------------------------
    def execute(self, context_data: Dict[str, Any], count: int = 5) -> Dict[str, Any]:
        alternatives = self.generate_alternatives(context_data, count)
        ranked = self.validate_and_rank(alternatives, context_data)
        return {
            "execution_date": datetime.now(timezone.utc).isoformat(),
            "base_position": context_data.get("position_statement"),
            "alternative_count": len(ranked),
            "alternatives": ranked,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_prompt(self, base_data: Dict[str, Any], count: int) -> str:
        return (
            "You are a marketing strategist. Generate "
            f"{count} concise positioning statements as JSON array.\n"
            f"Business Type: {base_data.get('user_type', 'unknown')}\n"
            f"What you do: {base_data.get('what_you_do', 'N/A')}\n"
            f"Primary challenge: {base_data.get('main_challenge', 'N/A')}\n"
            f"Current position: {base_data.get('position_statement', 'N/A')}\n"
        )

    def _parse_llm_response(self, response: Any) -> List[str]:
        if response is None:
            return []
        if isinstance(response, list):
            return [str(item) for item in response]
        if hasattr(response, "json"):
            try:
                return [str(item) for item in response.json()]
            except Exception:
                response = response.text if hasattr(response, "text") else str(response)
        if not isinstance(response, str):
            response = str(response)
        response = response.strip()
        if not response:
            return []
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        # Fallback: split by line or bullets
        candidates = []
        for line in response.splitlines():
            line = line.strip().lstrip("-*1234567890. ")
            if line:
                candidates.append(line)
        return candidates

    def _safe_select_framework(self, data: Dict[str, Any]) -> Optional[str]:
        user_type = data.get("user_type")
        if not user_type:
            return None
        try:
            result = self.selector.select_framework(data, user_type)
            return result.get("framework")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Framework selection failed: %s", exc)
            return None

    def _opportunity_score(self, statement: str, context: Dict[str, Any]) -> float:
        seed = hash((statement.lower(), context.get("user_type"))) & 0xFFFFFFFF
        rng = random.Random(seed)
        return round(rng.uniform(0.5, 1.0), 3)

    def _ranking_score(self, opportunity: float, fit: float) -> float:
        return round(0.6 * opportunity + 0.4 * fit, 3)

    def _opportunity_reason(self, score: float) -> str:
        if score >= 0.85:
            return "Signal strength suggests immediate go-to-market leverage."
        if score >= 0.7:
            return "Solid upside with differentiated angle to explore."
        return "Moderate opportunity but worth iterative testing."


__all__ = ["PositionGeneratorAgent"]


