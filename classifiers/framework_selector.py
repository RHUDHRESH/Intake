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
        # Analyze context for sophisticated framework matching
        context_analysis = self._analyze_user_context(answers, user_type)

        # Check for specific framework indicators
        framework_scores = self._calculate_framework_scores(answers, user_type, context_analysis)

        # Return best framework match
        if framework_scores:
            best_framework = max(framework_scores.items(), key=lambda x: x[1])
            if best_framework[1] > 0.7:  # Confidence threshold
                alternatives = [f for f, s in framework_scores.items() if s > 0.5 and f != best_framework[0]]
                return {
                    "framework": best_framework[0],
                    "confidence": best_framework[1],
                    "reasoning": self._generate_framework_reasoning(best_framework[0], context_analysis),
                    "alternatives": alternatives[:3]  # Top 3 alternatives
                }

        # Fallback to legacy logic for specific cases
        return self._legacy_framework_overrides(answers, user_type)

    def _analyze_user_context(self, answers: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Analyze user context for framework selection."""
        context = {
            "revenue_level": answers.get("annual_revenue", "unknown"),
            "growth_stage": answers.get("startup_stage", "unknown"),
            "primary_goal": answers.get("primary_goal", ""),
            "target_audience": answers.get("target_audience", ""),
            "marketing_budget": answers.get("marketing_budget", ""),
            "challenges": answers.get("challenges", []),
            "dream_outcome": answers.get("dream_outcome", ""),
            "user_type": user_type
        }

        # Extract key themes from text answers
        context["themes"] = self._extract_key_themes(answers)
        context["urgency_level"] = self._assess_urgency_level(answers)
        context["complexity_level"] = self._assess_complexity_level(answers)

        return context

    def _calculate_framework_scores(self, answers: Dict[str, Any], user_type: str, context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate relevance scores for each framework."""
        scores = {}

        for framework, characteristics in self.FRAMEWORK_CHARACTERISTICS.items():
            score = self._calculate_framework_relevance(framework, characteristics, context, user_type)
            if score > 0.3:  # Only include relevant frameworks
                scores[framework] = score

        return scores

    def _calculate_framework_relevance(self, framework: str, characteristics: Dict, context: Dict, user_type: str) -> float:
        """Calculate how relevant a framework is for the user's context."""
        score = 0.0
        reasons = []

        # Base score from user type alignment
        if user_type in self.BASE_FRAMEWORKS and self.BASE_FRAMEWORKS[user_type] == framework:
            score += 0.3
            reasons.append("user_type_alignment")

        # Score based on context match with framework characteristics
        context_keywords = self._extract_context_keywords(context)

        for keyword in context_keywords:
            if keyword in characteristics.get("best_for", []):
                score += 0.2
                reasons.append(f"keyword_match_{keyword}")
            if keyword in characteristics.get("focus", []):
                score += 0.15
                reasons.append(f"focus_match_{keyword}")

        # Adjust for complexity match
        complexity_match = self._check_complexity_match(characteristics["complexity"], context)
        score += complexity_match * 0.1

        # Boost for specific scenarios
        scenario_boost = self._calculate_scenario_boost(framework, context)
        score += scenario_boost

        return min(score, 1.0)  # Cap at 1.0

    def _extract_context_keywords(self, context: Dict[str, Any]) -> List[str]:
        """Extract key themes and keywords from user context."""
        keywords = []

        # Extract from primary goal
        goal = str(context.get("primary_goal", "")).lower()
        if "brand" in goal:
            keywords.extend(["personal_branding", "brand_building"])
        if "audience" in goal or "community" in goal:
            keywords.extend(["audience_building", "community_building"])
        if "viral" in goal or "spread" in goal:
            keywords.extend(["viral_potential", "word_of_mouth"])

        # Extract from challenges
        challenges = context.get("challenges", [])
        if isinstance(challenges, list):
            for challenge in challenges:
                challenge_str = str(challenge).lower()
                if "attention" in challenge_str or "engagement" in challenge_str:
                    keywords.append("attention_economy")
                if "positioning" in challenge_str or "competitive" in challenge_str:
                    keywords.extend(["market_positioning", "competitive_strategy"])

        # Extract from dream outcome
        dream = str(context.get("dream_outcome", "")).lower()
        if "media company" in dream or "content empire" in dream:
            keywords.extend(["media_company", "content_creator"])
        if "movement" in dream or "community" in dream:
            keywords.append("movement_creation")

        return list(set(keywords))  # Remove duplicates

    def _check_complexity_match(self, framework_complexity: str, context: Dict[str, Any]) -> float:
        """Check if framework complexity matches user needs."""
        urgency = context.get("urgency_level", "medium")
        user_complexity = context.get("complexity_level", "medium")

        # High urgency usually needs simpler frameworks
        if urgency == "high" and framework_complexity == "high":
            return -0.1
        if urgency == "low" and framework_complexity == "low":
            return -0.05

        # Match complexity preference
        complexity_scores = {"low": 0.1, "medium": 0.2, "high": 0.3}
        return complexity_scores.get(user_complexity, 0.1)

    def _calculate_scenario_boost(self, framework: str, context: Dict[str, Any]) -> float:
        """Calculate scenario-specific boosts for frameworks."""
        boost = 0.0

        # Permission marketing for trust-focused scenarios
        if framework == "Seth_Godin_Permission":
            trust_indicators = ["trust", "relationship", "loyalty", "permission"]
            context_text = str(context).lower()
            if any(indicator in context_text for indicator in trust_indicators):
                boost += 0.2

        # Purple Cow for differentiation needs
        elif framework == "Seth_Godin_Purple_Cow":
            diff_indicators = ["stand out", "unique", "remarkable", "different"]
            context_text = str(context).lower()
            if any(indicator in context_text for indicator in diff_indicators):
                boost += 0.2

        # Tribes for community building
        elif framework == "Seth_Godin_Tribes":
            community_indicators = ["community", "tribe", "movement", "leader"]
            context_text = str(context).lower()
            if any(indicator in context_text for indicator in community_indicators):
                boost += 0.2

        # Behavioral for psychological insights
        elif framework == "Rory_Sutherland_Behavioral":
            psych_indicators = ["behavior", "psychology", "human", "perception"]
            context_text = str(context).lower()
            if any(indicator in context_text for indicator in psych_indicators):
                boost += 0.15

        return boost

    def _generate_framework_reasoning(self, framework: str, context: Dict[str, Any]) -> str:
        """Generate human-readable reasoning for framework selection."""
        characteristics = self.FRAMEWORK_CHARACTERISTICS[framework]

        reasoning = f"Selected {framework} because "

        # Add primary reason based on best match
        if context.get("user_type") in self.BASE_FRAMEWORKS and self.BASE_FRAMEWORKS[context["user_type"]] == framework:
            reasoning += f"it aligns with {context['user_type']} businesses"
        else:
            reasoning += f"of your specific goals and challenges"

        reasoning += ". "

        # Add framework benefits
        reasoning += f"This framework focuses on {', '.join(characteristics['focus'][:2])} "
        reasoning += f"and is ideal for {', '.join(characteristics['best_for'][:2])} scenarios."

        return reasoning

    def _extract_key_themes(self, answers: Dict[str, Any]) -> List[str]:
        """Extract key themes from text answers."""
        themes = []
        text_answers = []

        # Collect all text-based answers
        for key, value in answers.items():
            if isinstance(value, str) and len(value) > 10:
                text_answers.append(value.lower())

        # Look for common themes
        theme_keywords = {
            "authenticity": ["authentic", "real", "genuine", "honest"],
            "community": ["community", "tribe", "group", "people"],
            "innovation": ["innovative", "new", "different", "unique"],
            "growth": ["grow", "scale", "expand", "increase"],
            "attention": ["attention", "awareness", "visibility", "noticed"]
        }

        for theme, keywords in theme_keywords.items():
            for answer in text_answers:
                if any(keyword in answer for keyword in keywords):
                    themes.append(theme)
                    break

        return themes

    def _assess_urgency_level(self, answers: Dict[str, Any]) -> str:
        """Assess urgency level from answers."""
        urgency_indicators = {
            "high": ["urgent", "asap", "quickly", "immediate", "deadline"],
            "low": ["patient", "long-term", "gradual", "slow build"]
        }

        combined_text = str(answers).lower()

        for level, indicators in urgency_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                return level

        return "medium"

    def _assess_complexity_level(self, answers: Dict[str, Any]) -> str:
        """Assess complexity preference from answers."""
        complexity_indicators = {
            "high": ["comprehensive", "detailed", "thorough", "complete"],
            "low": ["simple", "straightforward", "easy", "basic"]
        }

        combined_text = str(answers).lower()

        for level, indicators in complexity_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                return level

        return "medium"

    def _legacy_framework_overrides(self, answers: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Legacy framework override logic for backward compatibility."""
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

    def get_all_available_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """Get all available frameworks with their characteristics."""
        return self.FRAMEWORK_CHARACTERISTICS.copy()

    def get_framework_recommendations(self, answers: Dict[str, Any], user_type: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """Get top framework recommendations for the user."""
        context_analysis = self._analyze_user_context(answers, user_type)
        framework_scores = self._calculate_framework_scores(answers, user_type, context_analysis)

        # Sort by score and return top recommendations
        sorted_frameworks = sorted(framework_scores.items(), key=lambda x: x[1], reverse=True)

        recommendations = []
        for framework_name, score in sorted_frameworks[:top_n]:
            characteristics = self.FRAMEWORK_CHARACTERISTICS[framework_name]
            recommendations.append({
                "framework": framework_name,
                "score": score,
                "confidence": min(score * 100, 99),
                "description": characteristics["description"],
                "best_for": characteristics["best_for"][:3],  # Top 3 use cases
                "focus_areas": characteristics["focus"][:3],  # Top 3 focus areas
                "complexity": characteristics["complexity"],
                "reasoning": self._generate_framework_reasoning(framework_name, context_analysis)
            })

        return recommendations

    def compare_frameworks(self, framework1: str, framework2: str, answers: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Compare two frameworks for the user's context."""
        if framework1 not in self.FRAMEWORK_CHARACTERISTICS or framework2 not in self.FRAMEWORK_CHARACTERISTICS:
            return {"error": "One or both frameworks not found"}

        context_analysis = self._analyze_user_context(answers, user_type)
        scores = self._calculate_framework_scores(answers, user_type, context_analysis)

        score1 = scores.get(framework1, 0)
        score2 = scores.get(framework2, 0)

        return {
            "framework1": {
                "name": framework1,
                "score": score1,
                "characteristics": self.FRAMEWORK_CHARACTERISTICS[framework1]
            },
            "framework2": {
                "name": framework2,
                "score": score2,
                "characteristics": self.FRAMEWORK_CHARACTERISTICS[framework2]
            },
            "winner": framework1 if score1 > score2 else framework2,
            "margin": abs(score1 - score2),
            "context_analysis": context_analysis
        }
