"""Unit tests for adaptive questionnaire classifiers."""

import pytest

from classifiers import (
    AdaptiveQuestionnaire,
    BusinessTypeClassifier,
    FrameworkSelector,
)


def test_business_type_classifier_returns_metadata() -> None:
    classifier = BusinessTypeClassifier()
    result = classifier.classify({"user_type": "startup_founder"})

    assert result["business_type"] == "startup_founder"
    assert result["framework"] == "Switch 6"
    assert result["label"] == "Startup Founder"

    questions = classifier.get_classification_questions()
    assert questions[0]["id"] == "user_type"
    assert len(questions[0]["options"]) >= 5


def test_questionnaire_returns_progressive_batch() -> None:
    questionnaire = AdaptiveQuestionnaire()
    batch = questionnaire.get_questions_for_type("startup_founder")

    assert len(batch) == questionnaire.MAX_BATCH_SIZE
    ids = [q["id"] for q in batch]
    assert ids[0] == "location"
    assert "startup_stage" in ids


def test_questionnaire_follow_up_triggers() -> None:
    questionnaire = AdaptiveQuestionnaire()
    answers = {
        "current_marketing": ["None/very little"],
        "primary_goal": "Expand to new markets",
        "marketing_budget": "$10K-$25K",
    }
    follow_ups = questionnaire.get_follow_up_questions(answers, "business_owner")

    follow_up_ids = {item["id"] for item in follow_ups}
    assert {
        "why_no_marketing",
        "expansion_regions",
        "budget_expectations",
    }.issubset(follow_up_ids)


@pytest.mark.parametrize(
    "revenue,expected",
    [
        ("$5M+", "ADAPT"),
        ("$50K-$200K", "Switch 6"),
    ],
)
def test_framework_selector_overrides(revenue: str, expected: str) -> None:
    selector = FrameworkSelector()
    answers = {"annual_revenue": revenue}
    result = selector.select_framework(answers, "startup_founder")

    assert result["framework"] == expected
    assert 0.75 <= result["confidence"] <= 0.99
