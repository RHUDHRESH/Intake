"""LangGraph workflow that orchestrates the adaptive intake experience."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledGraph

from classifiers import (
    AdaptiveQuestionnaire,
    BusinessTypeClassifier,
    FrameworkSelector,
)


@dataclass
class IntakeDependencies:
    """Container for injectable dependencies used by the intake graph."""

    classifier: BusinessTypeClassifier
    questionnaire: AdaptiveQuestionnaire
    framework_selector: FrameworkSelector


class IntakeState(TypedDict, total=False):
    """State payload that flows through the adaptive intake graph."""

    answers: Dict[str, Any]
    answered_questions: List[str]
    classification: Dict[str, Any]
    user_type: str
    next_questions: List[Dict[str, Any]]
    follow_up_questions: List[Dict[str, Any]]
    validation: Dict[str, Any]
    framework: Dict[str, Any]
    is_complete: bool
    classification_questions: List[Dict[str, Any]]


def _default_dependencies() -> IntakeDependencies:
    return IntakeDependencies(
        classifier=BusinessTypeClassifier(),
        questionnaire=AdaptiveQuestionnaire(),
        framework_selector=FrameworkSelector(),
    )


def build_intake_graph(
    *,
    dependencies: Optional[IntakeDependencies] = None,
) -> StateGraph:
    """Construct the adaptive intake LangGraph workflow."""

    deps = dependencies or _default_dependencies()
    graph = StateGraph(IntakeState)

    def _ensure_defaults(state: IntakeState) -> IntakeState:
        answers = state.get("answers") or {}
        answered_questions = state.get("answered_questions") or list(answers.keys())
        return {
            **state,
            "answers": answers,
            "answered_questions": answered_questions,
        }

    def classify_node(state: IntakeState) -> IntakeState:
        state = _ensure_defaults(state)
        answers = state["answers"]
        classification = deps.classifier.classify(answers)
        user_type = classification.get("business_type")
        payload: IntakeState = {
            "classification": classification,
            "classification_questions": deps.classifier.get_classification_questions(),
        }
        if user_type and user_type != "unknown":
            payload["user_type"] = user_type
        return payload

    def question_batch_node(state: IntakeState) -> IntakeState:
        state = _ensure_defaults(state)
        answers = state["answers"]
        answered_questions = state["answered_questions"]
        user_type = state.get("user_type") or state.get("classification", {}).get("business_type")

        if not user_type or user_type == "unknown":
            return {
                "next_questions": deps.classifier.get_classification_questions(),
                "follow_up_questions": [],
                "is_complete": False,
            }

        next_questions = deps.questionnaire.get_questions_for_type(
            user_type, answered_questions
        )
        follow_ups = deps.questionnaire.get_follow_up_questions(answers, user_type)
        is_complete = not next_questions and not follow_ups
        return {
            "next_questions": next_questions,
            "follow_up_questions": follow_ups,
            "user_type": user_type,
            "is_complete": is_complete,
        }

    def validation_node(state: IntakeState) -> IntakeState:
        state = _ensure_defaults(state)
        user_type = state.get("user_type")
        if not user_type or user_type == "unknown":
            return {"validation": None, "is_complete": False}
        validation = deps.questionnaire.validate_responses(state["answers"], user_type)
        is_complete = bool(validation["valid"] and state.get("is_complete"))
        return {"validation": validation, "is_complete": is_complete}

    def framework_node(state: IntakeState) -> IntakeState:
        state = _ensure_defaults(state)
        user_type = state.get("user_type")
        if not user_type or user_type == "unknown":
            return {"framework": None, "is_complete": False}
        framework = deps.framework_selector.select_framework(
            state["answers"], user_type
        )
        is_complete = bool(state.get("is_complete") and state.get("validation", {}).get("valid"))
        return {"framework": framework, "is_complete": is_complete}

    graph.add_node("classify_user", classify_node)
    graph.add_node("question_batch", question_batch_node)
    graph.add_node("validate", validation_node)
    graph.add_node("select_framework", framework_node)

    graph.add_edge(START, "classify_user")
    graph.add_edge("classify_user", "question_batch")
    graph.add_edge("question_batch", "validate")
    graph.add_edge("validate", "select_framework")
    graph.add_edge("select_framework", END)

    return graph


def compile_intake_graph(
    *,
    dependencies: Optional[IntakeDependencies] = None,
) -> CompiledGraph:
    """Return a compiled version of the adaptive intake workflow."""

    graph = build_intake_graph(dependencies=dependencies)
    return graph.compile()
