from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from market_research.interfaces import PositionScoringModule

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


@dataclass
class Feedback:
    text: str
    severity: str
    reference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {"text": self.text, "severity": self.severity}
        if self.reference:
            payload["reference"] = self.reference
        return payload


class HeuristicScoringModule(PositionScoringModule):
    name = "heuristic"

    def __init__(self, *, weight: float = 1.0) -> None:
        self._weight = weight

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        score = self._score_statement(statement, context or {})
        feedback = [fb.to_dict() for fb in self._feedback(statement, context or {})]
        return {
            "module": self.name,
            "score": score,
            "weight": self._weight,
            "feedback": feedback,
            "mode": "heuristic",
        }

    def _score_statement(self, statement: str, context: Dict[str, Any]) -> float:
        return min(1.0, len(statement.strip()) / 120)

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        parts: List[Feedback] = []
        if len(statement.split()) < 6:
            parts.append(Feedback("Statement reads too short to convey value.", "warning"))
        if "we" not in statement.lower():
            parts.append(Feedback("Consider clarifying the actor/beneficiary.", "info"))
        return parts


class AdaptScoringModule(HeuristicScoringModule):
    name = "adapt"

    def _score_statement(self, statement: str, context: Dict[str, Any]) -> float:
        score = super()._score_statement(statement, context)
        if re.search(r"\b(problems?|challenges?|pain)\b", statement, re.IGNORECASE):
            score += 0.2
        if re.search(r"\bframework|diagnostic\b", statement, re.IGNORECASE):
            score += 0.1
        return min(score, 1.0)

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        items = super()._feedback(statement, context)
        if "problem" not in statement.lower():
            items.append(Feedback("Highlight the core audience pain more explicitly.", "warning"))
        return items


class Switch6ScoringModule(HeuristicScoringModule):
    name = "switch6"

    def _score_statement(self, statement: str, context: Dict[str, Any]) -> float:
        score = super()._score_statement(statement, context)
        for keyword in ("segment", "wound", "reframe", "offer", "action", "cash"):
            if keyword in statement.lower():
                score += 0.05
        return min(score, 1.0)

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        items = super()._feedback(statement, context)
        if "offer" not in statement.lower():
            items.append(Feedback("Call out the offer or proof to anchor value.", "info"))
        if "action" not in statement.lower():
            items.append(Feedback("Suggest next step to reinforce CTA strength.", "info"))
        return items


class OgilvyScoringModule(HeuristicScoringModule):
    name = "ogilvy"

    def _score_statement(self, statement: str, context: Dict[str, Any]) -> float:
        score = super()._score_statement(statement, context)
        if re.search(r"\b(results?|roi|conversion)\b", statement, re.IGNORECASE):
            score += 0.2
        if re.search(r"\bproof|case study\b", statement, re.IGNORECASE):
            score += 0.1
        return min(score, 1.0)

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        items = super()._feedback(statement, context)
        if "because" not in statement.lower():
            items.append(Feedback("Add 'because' clause to link proof with promise.", "warning"))
        return items


class GodinScoringModule(HeuristicScoringModule):
    name = "godin"

    def _score_statement(self, statement: str, context: Dict[str, Any]) -> float:
        score = super()._score_statement(statement, context)
        if re.search(r"remarkable|tribe|story|status", statement, re.IGNORECASE):
            score += 0.25
        return min(score, 1.0)

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        items = super()._feedback(statement, context)
        if "story" not in statement.lower():
            items.append(Feedback("Consider emphasising the story behind the shift.", "info"))
        return items


class LLMFeedbackMixin:
    """Adds agentic LLM clarification when credentials exist."""

    def _maybe_llm_feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or OpenAI is None:  # pragma: no cover
            return []
        client = OpenAI(api_key=api_key)
        completion = client.responses.create(
            model="gpt-4o-mini",
            input=f"Provide two short critiques for positioning statement: {statement}",
            temperature=0.3,
        )
        text = " ".join(choice.output_text for choice in completion.output)
        bullets = [item.strip() for item in text.split("\n") if item.strip()]
        return [Feedback(bullet, "info") for bullet in bullets[:2]]


class HybridScoringModule(LLMFeedbackMixin, HeuristicScoringModule):
    name = "hybrid"

    def _feedback(self, statement: str, context: Dict[str, Any]) -> List[Feedback]:
        base = super()._feedback(statement, context)
        return base + self._maybe_llm_feedback(statement, context)


__all__ = [
    "AdaptScoringModule",
    "GodinScoringModule",
    "HeuristicScoringModule",
    "HybridScoringModule",
    "OgilvyScoringModule",
    "Switch6ScoringModule",
]
