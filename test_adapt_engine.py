import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frameworks.adapt_engine import ADAPTFrameworkEngine


def test_adapt_framework_complete():
    """Test complete ADAPT framework execution"""

    print("[TEST] ADAPT FRAMEWORK ENGINE")
    print("-" * 50)

    # Initialize engine
    adapt_engine = ADAPTFrameworkEngine()

    # Sample questionnaire data (business owner)
    sample_data = {
        "user_type": "business_owner",
        "location": "Chennai, India",
        "primary_goal": "Generate more leads",
        "what_you_do": "We help small restaurants increase customer footfall through social media marketing",
        "why_story": "Started this after seeing too many great local restaurants struggle with empty tables",
        "target_customer": "Local restaurant owners aged 30-50 who are tech-savvy but lack marketing expertise",
        "main_challenge": "Converting social media engagement into actual customer visits",
        "marketing_budget": "$2K-$5K",
        "current_marketing": ["Social media posts", "Word of mouth"],
        "business_industry": "Digital Marketing for Restaurants",
        "annual_revenue": "$200K-$500K"
    }

    # Execute full ADAPT framework
    print("[RUN] Executing ADAPT Framework...")
    results = adapt_engine.execute_full_framework(sample_data)

    # Display results
    print(f"[INFO] Framework: {results['framework']}")
    print(f"[INFO] User Type: {results['user_type']}")
    print(f"[INFO] Overall Strength: {results['framework_strength']:.2f}")
    print()

    # Display each stage
    for stage_name, stage_data in results["stages"].items():
        print(f"[STAGE] {stage_data['stage'].upper()}")
        print(f"   Strength: {stage_data['stage_strength']:.2f}")

        if stage_name == "audience":
            print(f"   Primary Persona: {stage_data['primary_persona']['name']}")
            print(f"   Value Prop: {stage_data['value_proposition']['statement']}")
            print(f"   Key Pain Points: {', '.join(stage_data['pain_points'][:2])}")

        elif stage_name == "design":
            print(f"   Big Idea: {stage_data['big_idea']['concept']}")
            print(f"   Brand Voice: {stage_data['brand_voice']['tone']}")
            print(f"   Core Message: {stage_data['core_message'][:60]}...")

        elif stage_name == "assemble":
            print(f"   Content Calendar: {stage_data['content_calendar']}")
            print(f"   Tools: {', '.join(stage_data['tool_recommendations'][:3])}")

        elif stage_name == "promote":
            print(f"   Launch Plan: {stage_data['launch_plan']['soft_launch']}")
            print(f"   Community Tactics: {', '.join(stage_data['community_building'][:2])}")

        elif stage_name == "track":
            print(f"   Key Metrics: {', '.join(stage_data['key_metrics']['primary'][:2])}")
            print(f"   Review Frequency: {stage_data['measurement_plan']['frequency']}")

        print()

    # Display recommendations
    print("[IDEAS] RECOMMENDATIONS:")
    for i, rec in enumerate(results["recommendations"], 1):
        print(f"   {i}. {rec}")

    print()
    print("[DONE] ADAPT FRAMEWORK ENGINE TEST COMPLETED!")

    # Validate framework strength calculation
    assert 0.0 <= results["framework_strength"] <= 1.0, "Framework strength should be between 0 and 1"
    assert len(results["stages"]) == 5, "Should have all 5 ADAPT stages"
    assert results["user_type"] == sample_data["user_type"], "User type should match input"

    return results


if __name__ == "__main__":
    test_results = test_adapt_framework_complete()

    # Save detailed results for analysis
    with open("adapt_framework_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)

    print("[FILE] Detailed results saved to adapt_framework_results.json")
