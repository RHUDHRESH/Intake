"""Integration tests covering the adaptive intake LangGraph workflow."""

from typing import Dict, List

from classifiers import AdaptiveQuestionnaire
from graphs import compile_intake_graph


def test_intake_graph_prompts_for_classification_when_unknown() -> None:
    graph = compile_intake_graph()
    result = graph.invoke({"answers": {}})

    assert result["classification"]["business_type"] == "unknown"
    next_questions = result["next_questions"]
    assert next_questions[0]["id"] == "user_type"
    assert result["framework"] is None
    assert result["validation"] is None


def test_intake_graph_completes_when_all_required_answers_present() -> None:
    questionnaire = AdaptiveQuestionnaire()
    universal_ids: List[str] = [q["id"] for q in questionnaire.UNIVERSAL_QUESTIONS]
    type_ids: List[str] = [
        q["id"] for q in questionnaire.TYPE_QUESTIONS["business_owner"]
    ]
    answered = universal_ids + type_ids + ["user_type"]

    answers: Dict[str, object] = {
        "user_type": "business_owner",
        "location": "Austin, USA",
        "primary_goal": "Generate more leads",
        "current_marketing": ["SEO", "Email marketing"],
        "business_age": "3-5 years",
        "business_industry": "B2B professional services with a distributed delivery model",
        "team_size": "6-20 people",
        "annual_revenue": "$500K-$1M",
        "target_customer": (
            "Mid-market operations leaders seeking scalable automation partners with long-term support"
        ),
        "main_challenge": (
            "Translating word-of-mouth success into predictable pipeline while maintaining service quality"
        ),
        "marketing_budget": "$2K-$5K",
    }

    graph = compile_intake_graph()
    result = graph.invoke({"answers": answers, "answered_questions": answered})

    assert result["validation"]["valid"] is True
    assert result["next_questions"] == []
    assert result["follow_up_questions"] == []
    assert result["framework"]["framework"] == "ADAPT"
    assert result["is_complete"] is True

