"""Scenario coverage for the Startup Founder questionnaire path."""

from classifiers.business_type_classifier import BusinessTypeClassifier
from classifiers.adaptive_questionnaire import AdaptiveQuestionnaire
from classifiers.framework_selector import FrameworkSelector


def test_startup_founder_flow() -> None:
    """Test Startup Founder specific branching and framework logic."""

    print("[STARTUP FOUNDER] Starting flow test")

    classifier = BusinessTypeClassifier()
    questionnaire = AdaptiveQuestionnaire()
    framework_selector = FrameworkSelector()

    answers = {"user_type": "startup_founder"}
    classification = classifier.classify(answers)

    print(f"classification: {classification}")
    assert classification["business_type"] == "startup_founder"
    assert classification["framework"] == "Switch 6"

    questions = questionnaire.get_questions_for_type("startup_founder", [])
    question_ids = [question["id"] for question in questions]
    print(f"first batch ids: {question_ids}")

    expected_startup_questions = {"startup_stage", "funding_status", "target_market", "growth_ambition"}
    all_startup_ids = {question["id"] for question in questionnaire.TYPE_QUESTIONS["startup_founder"]}
    assert expected_startup_questions.issubset(all_startup_ids)

    aggressive_answers = {
        "user_type": "startup_founder",
        "location": "Bangalore, India",
        "primary_goal": "Expand to new markets",
        "startup_stage": "Launched/early traction",
        "funding_status": "Seed round",
        "target_market": "B2B",
        "growth_ambition": "We want to go global and scale aggressively to 10x revenue in 2 years",
        "biggest_obstacle": "Getting enough qualified leads in new markets",
        "unique_value": "First AI-powered customer service platform specifically for Indian small businesses",
    }
    framework_result = framework_selector.select_framework(aggressive_answers, "startup_founder")
    print(f"framework aggressive: {framework_result}")

    early_stage_answers = {
        "user_type": "startup_founder",
        "startup_stage": "MVP development",
        "growth_ambition": "Aggressive scaling once we validate product-market fit",
        "funding_status": "Self-funded",
    }
    early_framework = framework_selector.select_framework(early_stage_answers, "startup_founder")
    print(f"framework early: {early_framework}")

    assert "switch 6" in framework_result["framework"].lower()
    assert early_framework["framework"] == "Switch 6"

    print("[STARTUP FOUNDER] Flow test passed")


if __name__ == "__main__":
    test_startup_founder_flow()
