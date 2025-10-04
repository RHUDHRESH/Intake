"""Scenario coverage for the Personal Brand questionnaire path."""

from classifiers.business_type_classifier import BusinessTypeClassifier
from classifiers.adaptive_questionnaire import AdaptiveQuestionnaire
from classifiers.framework_selector import FrameworkSelector


def test_personal_brand_flow() -> None:
    """Test Personal Brand question set and framework handling."""

    print("[PERSONAL BRAND] Starting flow test")

    classifier = BusinessTypeClassifier()
    questionnaire = AdaptiveQuestionnaire()
    framework_selector = FrameworkSelector()

    answers = {"user_type": "personal_brand"}
    classification = classifier.classify(answers)

    print(f"classification: {classification}")
    assert classification["business_type"] == "personal_brand"
    assert classification["framework"] == "Switch 6"

    pb_questions = questionnaire.TYPE_QUESTIONS["personal_brand"]
    pb_ids = [question["id"] for question in pb_questions]
    print(f"question ids: {pb_ids}")

    expected_ids = {"brand_niche", "current_following", "content_platforms", "monetization", "personal_story"}
    assert expected_ids.issubset(pb_ids)

    influencer_answers = {
        "user_type": "personal_brand",
        "location": "Mumbai, India",
        "primary_goal": "Build community/audience",
        "brand_niche": "Entrepreneurship and startup advice for Indian founders",
        "current_following": "25K-100K",
        "content_platforms": ["LinkedIn", "Twitter/X", "YouTube"],
        "monetization": ["Consulting/coaching", "Courses/digital products"],
        "personal_story": (
            "Built and sold two startups in India, now mentoring other founders. Started with minimal resources and learned through trial and error."
        ),
        "dream_outcome": "Become the go-to mentor for Indian startup founders and build a community of one million entrepreneurs",
    }

    validation = questionnaire.validate_responses(influencer_answers, "personal_brand")
    print(f"validation influencer: {validation}")

    framework_result = framework_selector.select_framework(influencer_answers, "personal_brand")
    print(f"framework influencer: {framework_result}")

    beginner_answers = {
        "user_type": "personal_brand",
        "brand_niche": "Fitness and nutrition for working professionals",
        "current_following": "Under 1K",
        "monetization": ["Not monetizing yet"],
        "personal_story": "Transformed personal health while working long consulting hours",
    }
    beginner_validation = questionnaire.validate_responses(beginner_answers, "personal_brand")
    print(f"validation beginner: {beginner_validation}")

    assert validation["valid"] is True
    assert validation["quality_score"] > 0.8
    assert framework_result["framework"] == "Switch 6"
    assert len(influencer_answers["personal_story"]) > 50
    assert beginner_validation["valid"] is False

    print("[PERSONAL BRAND] Flow test passed")


if __name__ == "__main__":
    test_personal_brand_flow()
