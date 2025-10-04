# Example of how to integrate ADAPT Framework with your questionnaire system

from classifiers.adaptive_questionnaire import AdaptiveQuestionnaire
from classifiers.framework_selector import FrameworkSelector
from frameworks.adapt_engine import ADAPTFrameworkEngine


def run_complete_intake_with_adapt():
    """Complete intake flow with ADAPT framework integration"""

    # Step 1: User completes questionnaire
    questionnaire = AdaptiveQuestionnaire()
    framework_selector = FrameworkSelector()
    adapt_engine = ADAPTFrameworkEngine()

    # Sample completed questionnaire data
    user_answers = {
        "user_type": "business_owner",
        "location": "Mumbai, India",
        "primary_goal": "Increase brand awareness",
        "what_you_do": "Premium coffee roasting and retail",
        "target_customer": "Urban professionals who appreciate specialty coffee",
        "main_challenge": "Standing out in crowded coffee market",
        "marketing_budget": "$5K-$10K",
        # ... more questionnaire data
    }

    # Step 2: Validate responses
    validation = questionnaire.validate_responses(user_answers, "business_owner")
    print(f"Questionnaire Validation: {validation}")

    # Step 3: Select framework (should return ADAPT for business owner)
    framework_selection = framework_selector.select_framework(user_answers, "business_owner")
    print(f"Selected Framework: {framework_selection['framework']}")

    # Step 4: Execute ADAPT framework if selected
    if framework_selection["framework"] in ["ADAPT", "Hybrid"]:
        adapt_results = adapt_engine.execute_full_framework(user_answers)

        print("\n[RESULT] ADAPT EXECUTION COMPLETE")
        print(f"Framework Strength: {adapt_results['framework_strength']:.2f}")

        # Return structured output for user
        return {
            "questionnaire_complete": validation["valid"],
            "framework_used": "ADAPT",
            "framework_strength": adapt_results["framework_strength"],
            "audience_insights": adapt_results["stages"]["audience"]["audience_insights"],
            "brand_strategy": adapt_results["stages"]["design"]["big_idea"],
            "action_plan": adapt_results["stages"]["assemble"]["assembly_checklist"],
            "success_metrics": adapt_results["stages"]["track"]["key_metrics"],
            "recommendations": adapt_results["recommendations"],
        }

    return {"error": "Framework not supported"}


# Test the integration
if __name__ == "__main__":
    result = run_complete_intake_with_adapt()
    print("Final Integration Result:", result)
