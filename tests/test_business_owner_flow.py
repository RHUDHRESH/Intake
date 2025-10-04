"""Scenario coverage for the Business Owner questionnaire path."""

from classifiers.business_type_classifier import BusinessTypeClassifier
from classifiers.adaptive_questionnaire import AdaptiveQuestionnaire
from classifiers.framework_selector import FrameworkSelector


def test_business_owner_complete_flow() -> None:
    """Test complete Business Owner questionnaire flow."""

    print("[BUSINESS OWNER] Starting flow test")

    classifier = BusinessTypeClassifier()
    questionnaire = AdaptiveQuestionnaire()
    framework_selector = FrameworkSelector()

    initial_answers = {"user_type": "business_owner"}
    classification = classifier.classify(initial_answers)

    print(f"classification: {classification}")
    assert classification["business_type"] == "business_owner"
    assert classification["framework"] == "ADAPT"

    questions = questionnaire.get_questions_for_type("business_owner", [])
    print(f"first batch count: {len(questions)}")
    assert questions, "Expected business owner questions to be returned"

    complete_answers = {
        "user_type": "business_owner",
        "location": "Chennai, India",
        "primary_goal": "Generate more leads",
        "current_marketing": ["Social media posts", "Networking/events"],
        "business_age": "3-5 years",
        "business_industry": "Digital Marketing Agency",
        "team_size": "6-20 people",
        "annual_revenue": "$200K-$500K",
        "target_customer": (
            "Small to medium businesses seeking digital marketing support, with a focus on restaurants and retail stores in Chennai"
        ),
        "main_challenge": "Finding qualified leads that convert to long-term clients",
        "marketing_budget": "$2K-$5K",
    }

    validation = questionnaire.validate_responses(complete_answers, "business_owner")
    print(f"validation: {validation}")

    framework_result = framework_selector.select_framework(complete_answers, "business_owner")
    print(f"framework: {framework_result}")

    follow_ups = questionnaire.get_follow_up_questions(complete_answers, "business_owner")
    print(f"follow ups: {follow_ups}")

    assert validation["valid"] is True
    assert validation["quality_score"] > 0.7
    assert framework_result["framework"] in {"ADAPT", "Hybrid"}
    assert framework_result["confidence"] > 0.7
    assert isinstance(follow_ups, list)

    print("[BUSINESS OWNER] Flow test passed")


if __name__ == "__main__":
    test_business_owner_complete_flow()
