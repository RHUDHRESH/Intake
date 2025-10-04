from typing import Dict, List, Any
from datetime import datetime

from .big_idea_pipeline import BigIdeaPipeline, BigIdeaRequest


class ADAPTFrameworkEngine:
    """
    Complete ADAPT Framework Engine based on RaptorFlow methodology:
    A - Audience Alignment
    D - Design & Differentiate
    A - Assemble & Automate
    P - Promote & Participate
    T - Track & Tweak
    """

    def __init__(self):
        self.framework_name = "ADAPT"
        self.stages = ["audience", "design", "assemble", "promote", "track"]
        self.big_idea_pipeline = BigIdeaPipeline()

    def execute_full_framework(self, questionnaire_data: Dict) -> Dict:
        """Execute complete ADAPT framework on user data"""

        results = {
            "framework": "ADAPT",
            "execution_date": datetime.now().isoformat(),
            "user_type": questionnaire_data.get("user_type"),
            "stages": {}
        }

        # Execute each ADAPT stage
        results["stages"]["audience"] = self.audience_alignment(questionnaire_data)
        results["stages"]["design"] = self.design_differentiate(questionnaire_data, results["stages"]["audience"])
        results["stages"]["assemble"] = self.assemble_automate(questionnaire_data, results["stages"]["design"])
        results["stages"]["promote"] = self.promote_participate(questionnaire_data, results["stages"]["assemble"])
        results["stages"]["track"] = self.track_tweak(questionnaire_data, results["stages"]["promote"])

        # Calculate overall framework strength
        results["framework_strength"] = self.calculate_framework_strength(results["stages"])
        results["recommendations"] = self.generate_recommendations(results["stages"])

        return results

    def audience_alignment(self, data: Dict) -> Dict:
        """
        Stage 1: Audience Alignment - Deep audience analysis
        Research target audience pain points, desires, language
        Identify value proposition and ensure customer-centric messaging
        """

        audience_analysis = {
            "stage": "Audience Alignment",
            "primary_persona": self._create_primary_persona(data),
            "pain_points": self._identify_pain_points(data),
            "value_proposition": self._craft_value_proposition(data),
            "customer_language": self._extract_customer_language(data),
            "audience_insights": self._generate_audience_insights(data),
            "stage_strength": 0.0
        }

        # Calculate stage completion strength
        audience_analysis["stage_strength"] = self._calculate_audience_strength(audience_analysis)

        return audience_analysis

    def design_differentiate(self, data: Dict, audience_data: Dict) -> Dict:
        """
        Stage 2: Design & Differentiate - Craft bold strategy and brand story
        Define core message, brand voice, unique angle, positioning against competitors
        Emphasize Purple Cow (Seth Godin) remarkability and Big Idea (David Ogilvy)
        """
        brand_voice = self._define_brand_voice(data)

        design_strategy = {
            "stage": "Design & Differentiate",
            "brand_voice": brand_voice,
            "core_message": self._craft_core_message(data, audience_data),
            "big_idea": self._generate_big_idea(data, audience_data, brand_voice),
            "unique_differentiators": self._identify_differentiators(data),
            "positioning_statement": self._create_positioning_statement(data, audience_data),
            "brand_story": self._craft_brand_story(data),
            "competitive_angle": self._analyze_competitive_positioning(data),
            "stage_strength": 0.0
        }

        design_strategy["stage_strength"] = self._calculate_design_strength(design_strategy)

        return design_strategy

    def assemble_automate(self, data: Dict, design_data: Dict) -> Dict:
        """
        Stage 3: Assemble & Automate - Build assets and systems for efficient execution
        Create content, set up distribution channels, implement automation
        Focus on smart assembly using templates and batch creation
        """

        assembly_plan = {
            "stage": "Assemble & Automate",
            "content_calendar": self._create_content_calendar(data, design_data),
            "marketing_assets": self._plan_marketing_assets(data, design_data),
            "automation_setup": self._recommend_automation(data),
            "channel_setup": self._plan_channel_setup(data),
            "content_templates": self._generate_content_templates(data, design_data),
            "tool_recommendations": self._recommend_tools(data),
            "assembly_checklist": self._create_assembly_checklist(data),
            "stage_strength": 0.0
        }

        assembly_plan["stage_strength"] = self._calculate_assemble_strength(assembly_plan)

        return assembly_plan

    def promote_participate(self, data: Dict, assembly_data: Dict) -> Dict:
        """
        Stage 4: Promote & Participate - Launch campaigns and actively engage
        Drive awareness, run campaigns, foster two-way interaction
        Build community and encourage user-generated content (AISAS model)
        """

        promotion_strategy = {
            "stage": "Promote & Participate",
            "launch_plan": self._create_launch_plan(data, assembly_data),
            "campaign_timeline": self._generate_campaign_timeline(data),
            "engagement_strategy": self._plan_engagement_strategy(data),
            "community_building": self._recommend_community_tactics(data),
            "partnership_opportunities": self._identify_partnerships(data),
            "aisas_integration": self._apply_aisas_model(data, assembly_data),
            "participation_guidelines": self._create_participation_guidelines(data),
            "stage_strength": 0.0
        }

        promotion_strategy["stage_strength"] = self._calculate_promote_strength(promotion_strategy)

        return promotion_strategy

    def track_tweak(self, data: Dict, promotion_data: Dict) -> Dict:
        """
        Stage 5: Track & Tweak - Measure performance and iterate
        Monitor KPIs, collect feedback, identify patterns, implement improvements
        Close the loop back to Audience Alignment with new insights
        """

        tracking_framework = {
            "stage": "Track & Tweak",
            "key_metrics": self._define_key_metrics(data),
            "measurement_plan": self._create_measurement_plan(data, promotion_data),
            "feedback_collection": self._plan_feedback_collection(data),
            "analytics_setup": self._recommend_analytics_tools(data),
            "optimization_areas": self._identify_optimization_opportunities(data),
            "iteration_schedule": self._plan_iteration_schedule(data),
            "loop_back_insights": self._generate_loop_back_insights(data),
            "stage_strength": 0.0
        }

        tracking_framework["stage_strength"] = self._calculate_track_strength(tracking_framework)

        return tracking_framework

    # PRIVATE HELPER METHODS FOR EACH STAGE

    def _create_primary_persona(self, data: Dict) -> Dict:
        """Create detailed customer persona based on questionnaire data"""
        user_type = data.get("user_type", "business_owner")
        target_customer = data.get("target_customer", "")
        location = data.get("location", "")

        # Generate persona based on user type and inputs
        persona_templates = {
            "business_owner": {
                "name": "Business Betty",
                "role": "Small business owner",
                "challenges": ["Limited marketing budget", "Time constraints", "Unclear ROI"],
                "goals": ["Increase revenue", "Build brand awareness", "Streamline operations"]
            },
            "startup_founder": {
                "name": "Startup Sam",
                "role": "Tech entrepreneur",
                "challenges": ["Product-market fit", "User acquisition", "Funding pressure"],
                "goals": ["Scale quickly", "Validate product", "Attract investors"]
            },
            "personal_brand": {
                "name": "Creator Chris",
                "role": "Content creator/influencer",
                "challenges": ["Audience growth", "Monetization", "Content consistency"],
                "goals": ["Build following", "Create income streams", "Establish expertise"]
            }
        }

        base_persona = persona_templates.get(user_type, persona_templates["business_owner"])

        return {
            "name": base_persona["name"],
            "description": f"{base_persona['role']} in {location}" if location else base_persona["role"],
            "key_challenges": base_persona["challenges"],
            "primary_goals": base_persona["goals"],
            "target_description": target_customer or f"Ideal customer for {user_type}"
        }

    def _identify_pain_points(self, data: Dict) -> List[str]:
        """Extract and analyze customer pain points"""
        pain_points = []

        # Extract from various questionnaire fields
        if data.get("main_challenge"):
            pain_points.append(data["main_challenge"])
        if data.get("biggest_obstacle"):
            pain_points.append(data["biggest_obstacle"])
        if data.get("biggest_challenge"):
            pain_points.append(data["biggest_challenge"])

        # Add type-specific pain points
        user_type = data.get("user_type")
        type_pain_points = {
            "business_owner": ["Cash flow management", "Customer acquisition", "Competition"],
            "startup_founder": ["Market validation", "Funding runway", "Team building"],
            "personal_brand": ["Audience engagement", "Content ideas", "Platform algorithms"],
            "freelancer": ["Client acquisition", "Pricing", "Work-life balance"],
            "nonprofit_leader": ["Donor fatigue", "Awareness", "Resource constraints"]
        }

        pain_points.extend(type_pain_points.get(user_type, []))

        return list(set(pain_points))  # Remove duplicates

    def _craft_value_proposition(self, data: Dict) -> Dict:
        """Generate clear value proposition connecting offering to customer needs"""
        what_you_do = data.get("what_you_do", "")
        why_story = data.get("why_story", "")
        unique_value = data.get("unique_value", "")

        # Template-based value prop generation
        value_prop_template = f"We help {data.get('target_customer', 'our customers')} {self._extract_main_benefit(data)} so they can {self._extract_desired_outcome(data)}."

        return {
            "statement": value_prop_template,
            "key_benefit": self._extract_main_benefit(data),
            "target_outcome": self._extract_desired_outcome(data),
            "differentiator": unique_value or self._generate_differentiator(data),
            "emotional_hook": self._extract_emotional_element(why_story)
        }

    def _extract_customer_language(self, data: Dict) -> Dict:
        """Analyze language patterns from customer-focused responses"""
        customer_language = {
            "key_phrases": [],
            "tone": "professional",  # Default
            "pain_language": [],
            "outcome_language": []
        }

        # Extract language from customer descriptions
        target_customer = data.get("target_customer", "")
        if target_customer:
            # Simple keyword extraction (in production, use NLP)
            customer_language["key_phrases"] = self._extract_keywords(target_customer)

        # Determine tone based on user type and industry
        user_type = data.get("user_type")
        if user_type in ["personal_brand", "content_creator"]:
            customer_language["tone"] = "casual"
        elif user_type in ["b2b_saas", "corporate_marketer"]:
            customer_language["tone"] = "professional"
        else:
            customer_language["tone"] = "friendly"

        return customer_language

    def _generate_audience_insights(self, data: Dict) -> List[str]:
        """Generate actionable audience insights"""
        insights = []

        # Location-based insights
        location = data.get("location", "")
        if "India" in location:
            insights.extend([
                "Consider mobile-first content approach",
                "WhatsApp Business could be effective channel",
                "Regional language content may improve engagement"
            ])

        # Budget-based insights
        budget = data.get("marketing_budget", "")
        if "Under" in budget or "500" in budget:
            insights.append("Focus on organic growth and community building")

        # Type-specific insights
        user_type = data.get("user_type")
        type_insights = {
            "startup_founder": ["Leverage founder's personal story", "Focus on growth metrics"],
            "personal_brand": ["Consistency across platforms is crucial", "Authentic storytelling wins"],
            "local_business": ["Local SEO is essential", "Customer reviews drive trust"]
        }

        insights.extend(type_insights.get(user_type, []))

        return insights

    def _calculate_audience_strength(self, audience_data: Dict) -> float:
        """Calculate strength score for Audience Alignment stage (0-1)"""
        score = 0.0
        max_score = 5.0

        # Check persona completeness
        if audience_data["primary_persona"].get("target_description"):
            score += 1.0

        # Check pain points identification
        if len(audience_data["pain_points"]) >= 2:
            score += 1.0

        # Check value proposition clarity
        if len(audience_data["value_proposition"]["statement"]) > 20:
            score += 1.0

        # Check customer language analysis
        if audience_data["customer_language"]["key_phrases"]:
            score += 1.0

        # Check insights generation
        if len(audience_data["audience_insights"]) >= 3:
            score += 1.0

        return min(score / max_score, 1.0)

    # Similar helper methods for other stages...
    def _define_brand_voice(self, data: Dict) -> Dict:
        """Define brand voice and personality"""
        user_type = data.get("user_type")

        voice_mapping = {
            "personal_brand": {"tone": "authentic", "personality": "relatable", "style": "conversational"},
            "startup_founder": {"tone": "innovative", "personality": "bold", "style": "inspiring"},
            "business_owner": {"tone": "trustworthy", "personality": "professional", "style": "clear"},
            "nonprofit_leader": {"tone": "compassionate", "personality": "mission-driven", "style": "emotional"}
        }

        return voice_mapping.get(user_type, voice_mapping["business_owner"])

    def _craft_core_message(self, data: Dict, audience_data: Dict) -> str:
        """Craft core marketing message"""
        value_prop = audience_data["value_proposition"]["statement"]
        differentiator = audience_data["value_proposition"]["differentiator"]

        return f"{value_prop} {differentiator}"

    def _generate_big_idea(self, data: Dict, audience_data: Dict, brand_voice: Dict[str, Any]) -> Dict:
        """Generate Big Idea using retrieval-augmented pipeline."""
        primary_persona = audience_data.get("primary_persona", {})
        value_prop = audience_data.get("value_proposition", {})
        persona_name = primary_persona.get("name", "target customers")
        target_description = (
            primary_persona.get("target_description")
            or primary_persona.get("description")
            or persona_name
        )
        benefit = (
            value_prop.get("target_outcome")
            or value_prop.get("key_benefit")
            or "achieve meaningful results"
        )
        benchmarks = (
            data.get("performance_benchmarks")
            or data.get("historical_metrics")
            or data.get("campaign_metrics")
        )
        if isinstance(benchmarks, dict):
            benchmarks_list = [benchmarks]
        elif isinstance(benchmarks, list):
            benchmarks_list = benchmarks
        else:
            benchmarks_list = None

        brand = (
            data.get("brand_name")
            or data.get("business_name")
            or data.get("company_name")
            or data.get("what_you_do", "Your Brand")
        )
        positioning_statement = (
            value_prop.get("statement")
            or data.get("positioning_statement")
            or audience_data.get("positioning_statement", "")
        )

        request = BigIdeaRequest(
            brand=brand,
            positioning_statement=positioning_statement,
            audience=target_description,
            benefit=benefit,
            emotional_hook=value_prop.get("emotional_hook"),
            product=data.get("what_you_do") or data.get("product_name"),
            benchmarks=benchmarks_list,
            brand_voice=brand_voice.get("tone") if isinstance(brand_voice, dict) else None,
            style=brand_voice.get("style") if isinstance(brand_voice, dict) else None,
        )

        pipeline_result = self.big_idea_pipeline.run(request)
        generated_headlines = pipeline_result.get("headlines") or []
        top_headline = generated_headlines[0].get("headline") if generated_headlines else None
        fallback_concept = f"Finally, {data.get('what_you_do', 'a solution')} That Actually Works"
        concept = top_headline or fallback_concept
        campaign_theme = f"Built for {persona_name}"

        return {
            "concept": concept,
            "tagline": self._generate_tagline(data),
            "campaign_theme": campaign_theme,
            "generated_headlines": generated_headlines,
            "inspiration_examples": pipeline_result.get("inspirations", []),
            "clarity_prompt": pipeline_result.get("prompt"),
            "dashboard": pipeline_result.get("dashboard"),
        }

    def _generate_tagline(self, data: Dict) -> str:
        """Generate memorable tagline"""
        what_you_do = data.get("what_you_do", "")
        if len(what_you_do) > 10:
            # Extract key benefit
            return f"{self._extract_main_benefit(data)} Made Simple"
        return "Excellence Delivered"

    def calculate_framework_strength(self, stages: Dict) -> float:
        """Calculate overall ADAPT framework strength"""
        stage_scores = [stage_data.get("stage_strength", 0.0) for stage_data in stages.values()]
        return sum(stage_scores) / len(stage_scores) if stage_scores else 0.0

    def generate_recommendations(self, stages: Dict) -> List[str]:
        """Generate actionable recommendations based on framework analysis"""
        recommendations = []

        for stage_name, stage_data in stages.items():
            strength = stage_data.get("stage_strength", 0.0)
            if strength < 0.7:
                stage_recommendations = {
                    "audience": "Strengthen audience research with surveys or customer interviews",
                    "design": "Clarify your unique value proposition and brand messaging",
                    "assemble": "Set up basic automation and content templates",
                    "promote": "Increase engagement and community building efforts",
                    "track": "Implement analytics and regular performance reviews"
                }
                recommendations.append(stage_recommendations.get(stage_name, f"Improve {stage_name} stage"))

        return recommendations

    # Additional helper methods for completeness...
    def _extract_main_benefit(self, data: Dict) -> str:
        """Extract main benefit from user descriptions"""
        what_you_do = data.get("what_you_do", "")
        if "save time" in what_you_do.lower():
            return "Save Time"
        elif "increase" in what_you_do.lower():
            return "Boost Results"
        elif "help" in what_you_do.lower():
            return "Get Help"
        return "Achieve Success"

    def _extract_desired_outcome(self, data: Dict) -> str:
        """Extract desired customer outcome"""
        primary_goal = data.get("primary_goal", "")
        if "revenue" in primary_goal.lower():
            return "increase revenue"
        elif "awareness" in primary_goal.lower():
            return "build brand awareness"
        elif "leads" in primary_goal.lower():
            return "generate more leads"
        return "achieve their goals"

    def _generate_differentiator(self, data: Dict) -> str:
        """Generate differentiator if not provided"""
        user_type = data.get("user_type")
        differentiators = {
            "personal_brand": "with authentic, relatable expertise",
            "startup_founder": "through innovative technology solutions",
            "business_owner": "with proven, reliable service"
        }
        return differentiators.get(user_type, "with our unique approach")

    def _extract_emotional_element(self, why_story: str) -> str:
        """Extract emotional hook from why story"""
        if not why_story:
            return "passion for helping others succeed"

        emotional_keywords = ["frustrated", "passion", "excited", "proud", "worried", "happy"]
        for keyword in emotional_keywords:
            if keyword in why_story.lower():
                return f"driven by {keyword}"

        return "committed to making a difference"

    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words
        stop_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        return list(set(keywords))

    # Placeholder methods for other stages (implement similarly)
    def _calculate_design_strength(self, design_data: Dict) -> float:
        return 0.8  # Placeholder

    def _create_content_calendar(self, data: Dict, design_data: Dict) -> Dict:
        return {"weekly_posts": 3, "monthly_campaigns": 1}  # Placeholder

    def _plan_marketing_assets(self, data: Dict, design_data: Dict) -> List[str]:
        return ["Social media posts", "Email templates", "Landing page"]  # Placeholder

    def _recommend_automation(self, data: Dict) -> List[str]:
        return ["Email sequences", "Social media scheduling", "Lead nurturing"]

    def _plan_channel_setup(self, data: Dict) -> Dict:
        current_marketing = data.get("current_marketing", [])
        return {"primary_channels": current_marketing[:3] if current_marketing else ["Website", "Social media"]}

    def _generate_content_templates(self, data: Dict, design_data: Dict) -> List[str]:
        return ["Blog post outline", "Social media captions", "Email newsletter"]

    def _recommend_tools(self, data: Dict) -> List[str]:
        budget = data.get("marketing_budget", "Under $500")
        if "Under" in budget:
            return ["Canva (free)", "Mailchimp (free tier)", "Buffer (free)"]
        else:
            return ["Adobe Creative Suite", "HubSpot", "Hootsuite Pro"]

    def _create_assembly_checklist(self, data: Dict) -> List[str]:
        return [
            "Create brand style guide",
            "Set up content templates",
            "Configure automation tools",
            "Prepare first month of content"
        ]

    def _calculate_assemble_strength(self, assembly_data: Dict) -> float:
        return 0.75  # Placeholder

    def _create_launch_plan(self, data: Dict, assembly_data: Dict) -> Dict:
        return {
            "soft_launch": "Week 1: Close network and early adopters",
            "public_launch": "Week 2: Full marketing campaign",
            "amplification": "Week 3-4: Partnership and PR outreach"
        }

    def _generate_campaign_timeline(self, data: Dict) -> Dict:
        return {
            "month_1": "Brand awareness campaign",
            "month_2": "Lead generation focus",
            "month_3": "Customer success stories"
        }

    def _plan_engagement_strategy(self, data: Dict) -> Dict:
        return {
            "response_time": "Within 2 hours during business hours",
            "content_mix": "80% value, 20% promotional",
            "community_guidelines": "Be authentic, helpful, and consistent"
        }

    def _recommend_community_tactics(self, data: Dict) -> List[str]:
        user_type = data.get("user_type")
        if user_type == "personal_brand":
            return ["Create Facebook group", "Host live Q&As", "Feature user stories"]
        elif user_type == "business_owner":
            return ["Customer testimonials", "Behind-the-scenes content", "Local partnerships"]
        return ["Build email community", "Encourage user-generated content", "Host virtual events"]

    def _identify_partnerships(self, data: Dict) -> List[str]:
        return ["Complementary businesses", "Industry influencers", "Local organizations"]

    def _apply_aisas_model(self, data: Dict, assembly_data: Dict) -> Dict:
        """Apply AISAS model (Attention, Interest, Search, Action, Share)"""
        return {
            "attention": "Eye-catching visuals and headlines",
            "interest": "Valuable content that solves problems",
            "search": "SEO-optimized content and local listings",
            "action": "Clear calls-to-action and simple conversion process",
            "share": "Encourage testimonials and referrals"
        }

    def _create_participation_guidelines(self, data: Dict) -> List[str]:
        return [
            "Respond to all comments within 24 hours",
            "Share behind-the-scenes content weekly",
            "Ask questions to encourage engagement",
            "Acknowledge and thank community members"
        ]

    def _calculate_promote_strength(self, promotion_data: Dict) -> float:
        return 0.85  # Placeholder

    def _define_key_metrics(self, data: Dict) -> Dict:
        primary_goal = data.get("primary_goal", "")

        if "awareness" in primary_goal.lower():
            return {
                "primary": ["Website traffic", "Social media reach", "Brand mention tracking"],
                "secondary": ["Email subscribers", "Social media followers"]
            }
        elif "leads" in primary_goal.lower():
            return {
                "primary": ["Lead generation", "Conversion rate", "Cost per lead"],
                "secondary": ["Email open rates", "Content engagement"]
            }
        else:
            return {
                "primary": ["Revenue", "Customer acquisition", "ROI"],
                "secondary": ["Customer satisfaction", "Retention rate"]
            }

    def _create_measurement_plan(self, data: Dict, promotion_data: Dict) -> Dict:
        return {
            "frequency": "Weekly reviews, monthly deep dives",
            "tools": ["Google Analytics", "Social media insights", "Email platform analytics"],
            "reporting": "Monthly dashboard with key insights and recommendations"
        }

    def _plan_feedback_collection(self, data: Dict) -> Dict:
        return {
            "methods": ["Customer surveys", "Social media polls", "Direct outreach"],
            "frequency": "Quarterly comprehensive, ongoing informal",
            "focus_areas": ["Product feedback", "Content preferences", "Channel effectiveness"]
        }

    def _recommend_analytics_tools(self, data: Dict) -> List[str]:
        budget = data.get("marketing_budget", "Under $500")
        if "Under" in budget:
            return ["Google Analytics (free)", "Facebook Insights (free)", "Email platform analytics"]
        else:
            return ["Google Analytics Pro", "Hootsuite Analytics", "HubSpot Analytics"]

    def _identify_optimization_opportunities(self, data: Dict) -> List[str]:
        return [
            "A/B test email subject lines",
            "Optimize social media posting times",
            "Improve website conversion funnel",
            "Refine target audience segments"
        ]

    def _plan_iteration_schedule(self, data: Dict) -> Dict:
        return {
            "weekly": "Performance review and minor tweaks",
            "monthly": "Content strategy adjustments",
            "quarterly": "Full ADAPT cycle review and strategic pivots"
        }

    def _generate_loop_back_insights(self, data: Dict) -> List[str]:
        return [
            "Update audience personas based on actual customer data",
            "Refine messaging based on high-performing content",
            "Adjust channel mix based on engagement metrics",
            "Evolve value proposition based on customer feedback"
        ]

    def _calculate_track_strength(self, tracking_data: Dict) -> float:
        return 0.70  # Placeholder
    def _identify_differentiators(self, data: Dict) -> List[str]:
        """Summarize what makes the offer stand out"""
        differentiators: List[str] = []

        explicit_value = data.get("unique_value")
        if explicit_value:
            differentiators.append(explicit_value)

        proof_points = data.get("proof_points", [])
        if isinstance(proof_points, list):
            differentiators.extend(proof_points)

        user_type = data.get("user_type")
        type_specific = {
            "startup_founder": ["Agile product roadmap", "Data-driven experimentation"],
            "business_owner": ["Local market expertise", "High-touch customer service"],
            "personal_brand": ["Authentic storytelling", "Direct audience connection"],
        }
        differentiators.extend(type_specific.get(user_type, []))

        if not differentiators:
            differentiators.append("Relentless focus on delivering measurable outcomes")

        return list(dict.fromkeys(differentiators))

    def _create_positioning_statement(self, data: Dict, audience_data: Dict) -> str:
        """Craft a concise positioning statement"""
        persona = audience_data.get("primary_persona", {}).get("name", "target customers")
        category = data.get("business_industry", data.get("category", "your market"))
        differentiator = audience_data.get("value_proposition", {}).get("differentiator", "a unique approach")
        result = audience_data.get("value_proposition", {}).get("target_outcome", "achieve their goals")

        return (
            f"For {persona}, we are the {category} partner that delivers {result} "
            f"{differentiator}."
        )

    def _craft_brand_story(self, data: Dict) -> str:
        """Build a simplified brand story arc"""
        origin = data.get("why_story", "We started to solve a clear gap in the market")
        mission = data.get("mission", "Our mission is to help customers win")
        impact = data.get("impact", "The result is a community that grows together")

        return (
            f"Origin: {origin}. Mission: {mission}. Impact: {impact}."
        )

    def _analyze_competitive_positioning(self, data: Dict) -> Dict:
        """Provide high-level competitive landscape analysis"""
        competitors = data.get("competitors", ["Local competitors", "Digital-first challengers"])
        if isinstance(competitors, str):
            competitors = [competitors]

        strengths = [
            "Clear audience focus",
            "Modular marketing execution",
            "Iterative optimization mindset",
        ]

        watchouts = data.get("market_watchouts", ["Rising ad costs", "Copycat offers"])
        if isinstance(watchouts, str):
            watchouts = [watchouts]

        return {
            "key_competitors": competitors,
            "strengths": strengths,
            "watchouts": watchouts,
        }
