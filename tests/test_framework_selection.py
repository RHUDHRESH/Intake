"""Targeted tests for framework selection overrides."""

from classifiers.framework_selector import FrameworkSelector


def test_framework_selection_logic() -> None:
    """Test framework selection routing and reasoning."""

    print("[FRAMEWORK] Starting selection test")

    selector = FrameworkSelector()

    high_revenue_answers = {
        "user_type": "business_owner",
        "annual_revenue": "$1M-$5M",
        "business_age": "5-10 years",
    }
    result1 = selector.select_framework(high_revenue_answers, "business_owner")
    print(f"high revenue: {result1}")
    assert result1["framework"] == "ADAPT"
    assert result1["confidence"] > 0.85

    aggressive_startup = {
        "user_type": "startup_founder",
        "startup_stage": "MVP development",
        "growth_ambition": "Aggressive scaling and global expansion",
    }
    result2 = selector.select_framework(aggressive_startup, "startup_founder")
    print(f"aggressive startup: {result2}")
    assert result2["framework"] == "Switch 6"

    complex_business = {
        "user_type": "agency_owner",
        "target_audience": ["Small businesses", "Startups", "Corporations", "Nonprofits"],
    }
    result3 = selector.select_framework(complex_business, "agency_owner")
    print(f"complex business: {result3}")
    assert result3["framework"] in {"Hybrid", "ADAPT"}

    personal_brand = {
        "user_type": "personal_brand",
        "current_following": "5K-25K",
    }
    result4 = selector.select_framework(personal_brand, "personal_brand")
    print(f"personal brand: {result4}")
    assert result4["framework"] == "Switch 6"

    corporate = {
        "user_type": "corporate_marketer",
        "team_size": "21-50 people",
    }
    result5 = selector.select_framework(corporate, "corporate_marketer")
    print(f"corporate: {result5}")
    assert result5["framework"] == "ADAPT"

    for output in [result1, result2, result4, result5]:
        assert output["confidence"] > 0.5
        assert len(output["reasoning"]) > 10

    print("[FRAMEWORK] Selection test passed")


if __name__ == "__main__":
    test_framework_selection_logic()
