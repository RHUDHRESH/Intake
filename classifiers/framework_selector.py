"""Framework selection logic that builds on questionnaire answers."""

from typing import Any, Dict, List


class FrameworkSelector:
    """Pick the most appropriate strategy framework for a respondent."""

    # All available frameworks with their characteristics
    FRAMEWORK_CHARACTERISTICS = {
        "ADAPT": {
            "description": "Comprehensive business strategy framework",
            "best_for": ["established_business", "high_revenue", "complex_operations", "enterprise"],
            "focus": ["systems", "processes", "scalability", "comprehensive_strategy"],
            "complexity": "high"
        },
        "Switch 6": {
            "description": "Momentum-driven growth playbook",
            "best_for": ["startup", "personal_brand", "content_creator", "aggressive_growth"],
            "focus": ["momentum", "speed", "positioning", "rapid_execution"],
            "complexity": "medium"
        },
        "Seth_Godin_Permission": {
            "description": "Permission-based marketing philosophy",
            "best_for": ["audience_building", "trust_focused", "long_term_relationships", "ethical_marketing"],
            "focus": ["permission", "trust", "gradual_conversion", "respectful_communication"],
            "complexity": "medium"
        },
        "Seth_Godin_Purple_Cow": {
            "description": "Remarkable product/service differentiation",
            "best_for": ["product_innovation", "competitive_markets", "brand_differentiation", "unique_positioning"],
            "focus": ["remarkable_features", "stand_out", "unique_value_proposition", "market_attention"],
            "complexity": "medium"
        },
        "Seth_Godin_Tribes": {
            "description": "Community building and leadership",
            "best_for": ["community_building", "movement_creation", "leadership_development", "tribal_marketing"],
            "focus": ["community", "leadership", "shared_values", "movement_building"],
            "complexity": "high"
        },
        "Seth_Godin_Ideavirus": {
            "description": "Viral growth through word-of-mouth",
            "best_for": ["viral_potential", "network_effects", "word_of_mouth", "rapid_spread"],
            "focus": ["contagious_ideas", "network_effects", "rapid_adoption", "organic_growth"],
            "complexity": "medium"
        },
        "Rory_Sutherland_Behavioral": {
            "description": "Behavioral economics and psychological insights",
            "best_for": ["consumer_behavior", "psychological_insights", "subtle_influences", "human_factors"],
            "focus": ["behavioral_economics", "psychology", "subtle_changes", "human_perception"],
            "complexity": "high"
        },
        "Al_Ries_Positioning": {
            "description": "Strategic positioning and category ownership",
            "best_for": ["market_positioning", "category_creation", "competitive_strategy", "brand_ownership"],
            "focus": ["positioning", "category_ownership", "competitive_advantage", "strategic_focus"],
            "complexity": "medium"
        },
        "Gary_Vee_Attention": {
            "description": "Real-time attention and trend monitoring",
            "best_for": ["social_media", "trend_monitoring", "attention_economy", "real_time_marketing"],
            "focus": ["attention_capture", "trends", "real_time", "social_engagement"],
            "complexity": "low"
        },
        "Gary_Vee_Crush_It": {
            "description": "Personal brand building and execution",
            "best_for": ["personal_branding", "hustle_culture", "execution_focus", "brand_building"],
            "focus": ["execution", "hustle", "personal_brand", "relentless_action"],
            "complexity": "medium"
        },
        "Gary_Vee_Authenticity": {
            "description": "Digital authenticity and empathy-driven marketing",
            "best_for": ["authenticity", "empathy", "digital_transformation", "human_connection"],
            "focus": ["authenticity", "empathy", "human_connection", "digital_honesty"],
            "complexity": "medium"
        }
    }

    BASE_FRAMEWORKS: Dict[str, str] = {
        "business_owner": "ADAPT",
        "startup_founder": "Switch 6",
        "personal_brand": "Gary_Vee_Crush_It",
        "nonprofit_leader": "Seth_Godin_Tribes",
        "freelancer": "Gary_Vee_Crush_It",
        "agency_owner": "Al_Ries_Positioning",
        "corporate_marketer": "ADAPT",
        "content_creator": "Seth_Godin_Ideavirus",
        "ecommerce_owner": "Gary_Vee_Attention",
        "b2b_saas": "Al_Ries_Positioning",
        "local_business": "Seth_Godin_Purple_Cow",
        "coach_educator": "Seth_Godin_Permission",
    }

    def select_framework(self, answers: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Select framework based on deep analysis of answers."""
        base_framework = self.BASE_FRAMEWORKS.get(user_type, "ADAPT")
        overrides = self._check_framework_overrides(answers, user_type)
        final_framework = overrides.get("framework") or base_framework
        confidence = overrides.get("confidence", 0.8 if final_framework == base_framework else 0.85)
        reasoning = overrides.get(
            "reasoning",
            f"Selected {final_framework} based on user type: {user_type}",
        )
        alternatives: List[str] = overrides.get("alternatives", [])

        if final_framework != base_framework and base_framework not in alternatives:
            alternatives.append(base_framework)

        return {
            "framework": final_framework,
            "confidence": min(confidence, 0.99),
            "reasoning": reasoning,
            "alternative_frameworks": sorted(set(alternatives)),
        }

    def _check_framework_overrides(
        self, answers: Dict[str, Any], user_type: str
    ) -> Dict[str, Any]:
        """Check for conditions that might override base framework selection."""
        revenue = answers.get("annual_revenue")
        if revenue in {"$1M-$5M", "$5M+"}:
            return {
                "framework": "ADAPT",
                "confidence": 0.9,
                "reasoning": "High revenue business benefits from comprehensive ADAPT framework",
            }

        startup_stage = answers.get("startup_stage")
        growth_ambition = str(answers.get("growth_ambition", "")).lower()
        if startup_stage in {"Idea stage", "MVP development"} and any(
            keyword in growth_ambition for keyword in {"aggressive", "hyper", "rapid"}
        ):
            return {
                "framework": "Switch 6",
                "confidence": 0.87,
                "reasoning": "Early stage with aggressive goals needs focused Switch 6 approach",
            }

        target_audience = answers.get("target_audience")
        if isinstance(target_audience, (list, tuple, set)) and len(target_audience) > 3:
            return {
                "framework": "Hybrid",
                "confidence": 0.75,
                "reasoning": "Multiple target audiences suggest hybrid approach needed",
                "alternatives": ["ADAPT", "Switch 6"],
            }

        marketing_budget = answers.get("marketing_budget")
        primary_goal = answers.get("primary_goal")
        if marketing_budget in {"Under $500", "$500-$2K"} and primary_goal in {
            "Expand to new markets",
            "Launch new product/service",
        }:
            return {
                "framework": "Switch 6",
                "confidence": 0.82,
                "reasoning": "Lean budgets with expansion goals need the momentum-driven Switch 6 playbook",
                "alternatives": ["ADAPT"],
            }

        if user_type == "b2b_saas" and self._any_answer_contains(answers.get("pipeline_challenges"), "enterprise"):
            return {
                "framework": "ADAPT",
                "confidence": 0.88,
                "reasoning": "Enterprise pipeline complexity aligns with ADAPT's systems focus",
            }

        if user_type == "content_creator" and self._any_answer_contains(
            answers.get("dream_outcome"), "media company"
        ):
            return {
                "framework": "Hybrid",
                "confidence": 0.8,
                "reasoning": "Creator aiming to become a media company benefits from blending Switch 6 and ADAPT",
                "alternatives": ["Switch 6", "ADAPT"],
            }

        return {"framework": None}

    @staticmethod
    def _any_answer_contains(answer: Any, keyword: str) -> bool:
        if isinstance(answer, str):
            return keyword.lower() in answer.lower()
        return False
