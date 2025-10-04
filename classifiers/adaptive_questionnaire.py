"""Adaptive questionnaire flow that tailors follow-up questions by user type."""

from typing import Any, Dict, Iterable, List, Optional, Sequence


def _is_answer_provided(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


class AdaptiveQuestionnaire:
    """Comprehensive questionnaire system with type-specific question flows."""

    MAX_BATCH_SIZE = 4

    UNIVERSAL_QUESTIONS: List[Dict[str, Any]] = [
        {
            "id": "location",
            "text": "Where are you located? (City, Country)",
            "type": "location",
            "google_maps": True,
            "required": True,
        },
        {
            "id": "primary_goal",
            "text": "What's your primary marketing goal right now?",
            "type": "single_choice",
            "options": [
                "Increase brand awareness",
                "Generate more leads",
                "Boost sales/revenue",
                "Build community/audience",
                "Launch new product/service",
                "Improve customer retention",
                "Expand to new markets",
            ],
            "required": True,
        },
        {
            "id": "current_marketing",
            "text": "What marketing are you currently doing?",
            "type": "multiple_choice",
            "options": [
                "Social media posts",
                "Paid advertising (Facebook/Google)",
                "Content marketing/blogging",
                "Email marketing",
                "SEO",
                "Networking/events",
                "Word of mouth",
                "None/very little",
            ],
        },
    ]

    TYPE_QUESTIONS: Dict[str, List[Dict[str, Any]]] = {
        "business_owner": [
            {
                "id": "business_age",
                "text": "How long has your business been operating?",
                "type": "single_choice",
                "options": [
                    "Under 1 year",
                    "1-3 years",
                    "3-5 years",
                    "5-10 years",
                    "10+ years",
                ],
            },
            {
                "id": "business_industry",
                "text": "What industry are you in?",
                "type": "text",
                "required": True,
            },
            {
                "id": "team_size",
                "text": "How many people work in your business?",
                "type": "single_choice",
                "options": [
                    "Just me",
                    "2-5 people",
                    "6-20 people",
                    "21-50 people",
                    "50+ people",
                ],
            },
            {
                "id": "annual_revenue",
                "text": "What's your approximate annual revenue?",
                "type": "single_choice",
                "options": [
                    "Under $50K",
                    "$50K-$200K",
                    "$200K-$500K",
                    "$500K-$1M",
                    "$1M-$5M",
                    "$5M+",
                ],
            },
            {
                "id": "target_customer",
                "text": "Who is your ideal customer? Be specific.",
                "type": "long_text",
                "required": True,
            },
            {
                "id": "main_challenge",
                "text": "What's your biggest business challenge right now?",
                "type": "text",
                "required": True,
            },
            {
                "id": "marketing_budget",
                "text": "What's your monthly marketing budget?",
                "type": "single_choice",
                "options": [
                    "Under $500",
                    "$500-$2K",
                    "$2K-$5K",
                    "$5K-$10K",
                    "$10K-$25K",
                    "$25K+",
                ],
            },
        ],
        "startup_founder": [
            {
                "id": "startup_stage",
                "text": "What stage is your startup?",
                "type": "single_choice",
                "options": [
                    "Idea stage",
                    "MVP development",
                    "Beta testing",
                    "Launched/early traction",
                    "Growth stage",
                ],
            },
            {
                "id": "funding_status",
                "text": "What's your funding situation?",
                "type": "single_choice",
                "options": [
                    "Self-funded",
                    "Angel investment",
                    "Seed round",
                    "Series A+",
                    "Seeking funding",
                ],
            },
            {
                "id": "target_market",
                "text": "What market are you targeting?",
                "type": "single_choice",
                "options": [
                    "B2B",
                    "B2C",
                    "B2B2C",
                    "Marketplace",
                    "Not sure yet",
                ],
            },
            {
                "id": "growth_ambition",
                "text": "What's your growth ambition?",
                "type": "text",
                "required": True,
            },
            {
                "id": "biggest_obstacle",
                "text": "What's your biggest obstacle to growth?",
                "type": "text",
                "required": True,
            },
            {
                "id": "competition",
                "text": "Who are your main competitors?",
                "type": "text",
            },
            {
                "id": "unique_value",
                "text": "What makes your startup unique?",
                "type": "long_text",
                "required": True,
            },
        ],
        "personal_brand": [
            {
                "id": "brand_niche",
                "text": "What niche/expertise do you want to be known for?",
                "type": "text",
                "required": True,
            },
            {
                "id": "current_following",
                "text": "What's your current social media following?",
                "type": "single_choice",
                "options": [
                    "Under 1K",
                    "1K-5K",
                    "5K-25K",
                    "25K-100K",
                    "100K+",
                ],
            },
            {
                "id": "content_platforms",
                "text": "Which platforms do you create content on?",
                "type": "multiple_choice",
                "options": [
                    "LinkedIn",
                    "Twitter/X",
                    "Instagram",
                    "YouTube",
                    "TikTok",
                    "Facebook",
                    "Newsletter/Blog",
                    "Podcast",
                ],
            },
            {
                "id": "monetization",
                "text": "How do you currently monetize (or plan to)?",
                "type": "multiple_choice",
                "options": [
                    "Consulting/coaching",
                    "Courses/digital products",
                    "Speaking",
                    "Sponsorships",
                    "Affiliate marketing",
                    "Books/content",
                    "Not monetizing yet",
                ],
            },
            {
                "id": "personal_story",
                "text": "What's your personal story/background that makes you credible?",
                "type": "long_text",
                "required": True,
            },
            {
                "id": "dream_outcome",
                "text": "What's your dream outcome from building your personal brand?",
                "type": "text",
                "required": True,
            },
        ],
        "nonprofit_leader": [
            {
                "id": "cause_focus",
                "text": "What cause/issue does your nonprofit address?",
                "type": "text",
                "required": True,
            },
            {
                "id": "nonprofit_size",
                "text": "What's the size of your nonprofit?",
                "type": "single_choice",
                "options": [
                    "Under $100K budget",
                    "$100K-$500K budget",
                    "$500K-$1M budget",
                    "$1M+ budget",
                ],
            },
            {
                "id": "target_audience",
                "text": "Who are you trying to reach?",
                "type": "multiple_choice",
                "options": [
                    "Donors",
                    "Volunteers",
                    "Beneficiaries",
                    "Government/policy makers",
                    "Corporate partners",
                    "General public",
                ],
            },
            {
                "id": "main_challenge",
                "text": "What's your biggest challenge in reaching people?",
                "type": "text",
                "required": True,
            },
            {
                "id": "success_story",
                "text": "What's your best success story/impact story?",
                "type": "long_text",
            },
        ],
        "freelancer": [
            {
                "id": "service_type",
                "text": "What services do you offer?",
                "type": "text",
                "required": True,
            },
            {
                "id": "experience_level",
                "text": "How long have you been freelancing?",
                "type": "single_choice",
                "options": [
                    "Under 6 months",
                    "6 months - 2 years",
                    "2-5 years",
                    "5+ years",
                ],
            },
            {
                "id": "client_type",
                "text": "What type of clients do you work with?",
                "type": "single_choice",
                "options": [
                    "Small businesses",
                    "Startups",
                    "Large corporations",
                    "Agencies",
                    "Mixed/various",
                ],
            },
            {
                "id": "pricing_model",
                "text": "How do you price your services?",
                "type": "single_choice",
                "options": [
                    "Hourly rate",
                    "Project-based",
                    "Retainer",
                    "Value-based",
                    "Mixed",
                ],
            },
            {
                "id": "biggest_challenge",
                "text": "What's your biggest challenge in getting clients?",
                "type": "text",
                "required": True,
            },
        ],
        "agency_owner": [
            {
                "id": "core_service_mix",
                "text": "What services make up the bulk of your retainers?",
                "type": "multiple_choice",
                "options": [
                    "Paid media",
                    "Organic social",
                    "Creative production",
                    "SEO/Content",
                    "Web development",
                    "Strategy/consulting",
                    "Analytics/Reporting",
                ],
            },
            {
                "id": "retainer_ratio",
                "text": "What percentage of revenue is retainer vs project work?",
                "type": "single_choice",
                "options": [
                    "All project",
                    "Mostly project",
                    "Even mix",
                    "Mostly retainers",
                    "All retainers",
                ],
            },
            {
                "id": "capacity",
                "text": "How many active clients can your team support right now?",
                "type": "single_choice",
                "options": [
                    "1-3",
                    "4-7",
                    "8-12",
                    "13-20",
                    "20+",
                ],
            },
            {
                "id": "client_acquisition",
                "text": "How do you acquire most of your clients today?",
                "type": "multiple_choice",
                "options": [
                    "Inbound referrals",
                    "Outbound sales",
                    "Partnerships",
                    "Content marketing",
                    "Paid ads",
                    "Events/conferences",
                ],
            },
            {
                "id": "avg_contract_value",
                "text": "What's your typical contract value?",
                "type": "single_choice",
                "options": [
                    "Under $5K",
                    "$5K-$10K",
                    "$10K-$25K",
                    "$25K-$50K",
                    "$50K+",
                ],
            },
            {
                "id": "differentiator",
                "text": "What makes your agency stand out in pitches?",
                "type": "long_text",
                "required": True,
            },
        ],
        "corporate_marketer": [
            {
                "id": "company_size",
                "text": "Roughly how many employees does your company have?",
                "type": "single_choice",
                "options": [
                    "Under 50",
                    "50-200",
                    "200-1K",
                    "1K-5K",
                    "5K+",
                ],
            },
            {
                "id": "department_structure",
                "text": "What's your marketing team structure?",
                "type": "text",
                "required": True,
            },
            {
                "id": "budget_authority",
                "text": "Do you control the marketing budget?",
                "type": "single_choice",
                "options": [
                    "I own the budget",
                    "Shared ownership",
                    "Influence only",
                    "No budget authority",
                ],
            },
            {
                "id": "stakeholder_alignment",
                "text": "Who are the key stakeholders you need to align with?",
                "type": "long_text",
            },
            {
                "id": "primary_channel",
                "text": "Which channel is most critical for your KPIs?",
                "type": "single_choice",
                "options": [
                    "Paid media",
                    "Owned content",
                    "Events",
                    "Sales enablement",
                    "Partner marketing",
                    "Other",
                ],
            },
            {
                "id": "measurement_tools",
                "text": "What tools do you rely on for measurement?",
                "type": "multiple_choice",
                "options": [
                    "GA4",
                    "Tableau/BI",
                    "CRM reports",
                    "Attribution platform",
                    "Custom dashboards",
                    "Spreadsheets",
                ],
            },
            {
                "id": "internal_challenges",
                "text": "What's your top internal challenge right now?",
                "type": "text",
                "required": True,
            },
        ],
        "content_creator": [
            {
                "id": "content_formats",
                "text": "What formats do you produce most often?",
                "type": "multiple_choice",
                "options": [
                    "Short-form video",
                    "Long-form video",
                    "Livestreams",
                    "Articles/newsletters",
                    "Audio/podcasts",
                    "Photography",
                ],
            },
            {
                "id": "posting_cadence",
                "text": "How often do you publish new content?",
                "type": "single_choice",
                "options": [
                    "Daily",
                    "Several times a week",
                    "Weekly",
                    "Bi-weekly",
                    "Monthly",
                ],
            },
            {
                "id": "team_support",
                "text": "Who helps you with production right now?",
                "type": "multiple_choice",
                "options": [
                    "It's just me",
                    "Editor",
                    "Videographer",
                    "Writer",
                    "Community manager",
                    "Agency",
                ],
            },
            {
                "id": "brand_partnerships",
                "text": "What brand partnerships have you done so far?",
                "type": "long_text",
            },
            {
                "id": "growth_tactics",
                "text": "What tactics have worked best for growth?",
                "type": "text",
                "required": True,
            },
            {
                "id": "audience_demographics",
                "text": "Who makes up your audience today?",
                "type": "text",
            },
        ],
        "ecommerce_owner": [
            {
                "id": "product_catalog_size",
                "text": "Roughly how many SKUs do you manage?",
                "type": "single_choice",
                "options": [
                    "Under 10",
                    "10-50",
                    "50-200",
                    "200-1000",
                    "1000+",
                ],
            },
            {
                "id": "sales_channels",
                "text": "Where do you currently sell?",
                "type": "multiple_choice",
                "options": [
                    "Own website",
                    "Amazon",
                    "Etsy",
                    "Retail",
                    "Wholesale",
                    "Other marketplaces",
                ],
            },
            {
                "id": "conversion_rate",
                "text": "What's your current store conversion rate (approx)?",
                "type": "single_choice",
                "options": [
                    "Under 1%",
                    "1-2%",
                    "2-3%",
                    "3-4%",
                    "4%+",
                    "Not sure",
                ],
            },
            {
                "id": "average_order_value",
                "text": "What's your average order value?",
                "type": "single_choice",
                "options": [
                    "Under $25",
                    "$25-$75",
                    "$75-$150",
                    "$150-$300",
                    "$300+",
                ],
            },
            {
                "id": "inventory_challenges",
                "text": "Any inventory or fulfillment challenges?",
                "type": "text",
                "required": True,
            },
            {
                "id": "customer_lifetime_value",
                "text": "What is your estimated customer lifetime value?",
                "type": "text",
            },
        ],
        "b2b_saas": [
            {
                "id": "acv",
                "text": "What's your average contract value (ACV)?",
                "type": "single_choice",
                "options": [
                    "Under $1K",
                    "$1K-$5K",
                    "$5K-$20K",
                    "$20K-$50K",
                    "$50K+",
                ],
            },
            {
                "id": "sales_motion",
                "text": "What's your primary sales motion?",
                "type": "single_choice",
                "options": [
                    "PLG/self-serve",
                    "Inbound sales",
                    "Outbound sales",
                    "Channel/partner",
                    "Mixed",
                ],
            },
            {
                "id": "customer_segments",
                "text": "Who are your core customer segments?",
                "type": "text",
                "required": True,
            },
            {
                "id": "trial_model",
                "text": "Do you offer a trial or freemium tier?",
                "type": "single_choice",
                "options": [
                    "Free trial",
                    "Freemium",
                    "Demo only",
                    "Paid pilot",
                    "No trial",
                ],
            },
            {
                "id": "churn_rate",
                "text": "What's your current churn rate?",
                "type": "single_choice",
                "options": [
                    "Under 3%",
                    "3-5%",
                    "5-8%",
                    "8-12%",
                    "12%+",
                    "Unsure",
                ],
            },
            {
                "id": "pipeline_challenges",
                "text": "Where does your revenue pipeline stall most often?",
                "type": "text",
                "required": True,
            },
            {
                "id": "product_marketing_alignment",
                "text": "How aligned are product and marketing today?",
                "type": "text",
            },
        ],
        "local_business": [
            {
                "id": "storefront_type",
                "text": "What type of location do you operate?",
                "type": "single_choice",
                "options": [
                    "Retail storefront",
                    "Service office",
                    "Restaurant/Food",
                    "Multi-location",
                    "Mobile/field",
                ],
            },
            {
                "id": "local_competition",
                "text": "How competitive is your local market?",
                "type": "single_choice",
                "options": [
                    "Just a few competitors",
                    "Crowded market",
                    "Regional players",
                    "National chains",
                    "Not sure",
                ],
            },
            {
                "id": "foot_traffic",
                "text": "How do you currently drive foot traffic or bookings?",
                "type": "text",
                "required": True,
            },
            {
                "id": "service_area",
                "text": "Which neighborhoods or regions do you serve?",
                "type": "text",
            },
            {
                "id": "review_strategy",
                "text": "What's your approach to managing online reviews?",
                "type": "text",
            },
            {
                "id": "community_involvement",
                "text": "Do you participate in community organizations or events?",
                "type": "single_choice",
                "options": [
                    "Regularly",
                    "Occasionally",
                    "Rarely",
                    "Not yet",
                ],
            },
        ],
        "coach_educator": [
            {
                "id": "delivery_model",
                "text": "How do you deliver your coaching/education today?",
                "type": "multiple_choice",
                "options": [
                    "1:1 sessions",
                    "Group programs",
                    "Online course",
                    "Membership",
                    "Workshops/retreats",
                    "Corporate training",
                ],
            },
            {
                "id": "certifications",
                "text": "Do you hold any certifications or accreditations?",
                "type": "text",
            },
            {
                "id": "program_price_point",
                "text": "What's your flagship offer price point?",
                "type": "single_choice",
                "options": [
                    "Under $500",
                    "$500-$1K",
                    "$1K-$3K",
                    "$3K-$7K",
                    "$7K+",
                ],
            },
            {
                "id": "group_vs_one_on_one",
                "text": "What percentage of revenue is group vs 1:1?",
                "type": "single_choice",
                "options": [
                    "All 1:1",
                    "Mostly 1:1",
                    "Even split",
                    "Mostly group",
                    "All group",
                ],
            },
            {
                "id": "student_results",
                "text": "What results are your clients most proud of?",
                "type": "long_text",
                "required": True,
            },
            {
                "id": "content_library_size",
                "text": "How extensive is your existing curriculum or content library?",
                "type": "text",
            },
            {
                "id": "scalability_challenge",
                "text": "What's the main bottleneck to scaling your impact?",
                "type": "text",
                "required": True,
            },
        ],
    }
    def get_questions_for_type(
        self,
        user_type: str,
        answered_questions: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return the next batch of questions respecting progressive disclosure."""
        answered_ids = set(answered_questions or [])
        questions: List[Dict[str, Any]] = [
            q
            for q in self.UNIVERSAL_QUESTIONS
            if q["id"] not in answered_ids
        ]
        if user_type in self.TYPE_QUESTIONS:
            type_specific = [
                q
                for q in self.TYPE_QUESTIONS[user_type]
                if q["id"] not in answered_ids
            ]
            questions.extend(type_specific)
        return questions[: self.MAX_BATCH_SIZE]

    def validate_responses(self, answers: Dict[str, Any], user_type: str) -> Dict[str, Any]:
        """Validate that required questions are present and score response quality."""
        required_universal = [
            q["id"] for q in self.UNIVERSAL_QUESTIONS if q.get("required")
        ]
        required_type_specific = [
            q["id"]
            for q in self.TYPE_QUESTIONS.get(user_type, [])
            if q.get("required")
        ]
        all_expected = [
            q["id"] for q in self.UNIVERSAL_QUESTIONS
        ] + [
            q["id"] for q in self.TYPE_QUESTIONS.get(user_type, [])
        ]

        missing = [
            req_id
            for req_id in required_universal + required_type_specific
            if not _is_answer_provided(answers.get(req_id))
        ]

        total_required = len(required_universal) + len(required_type_specific)
        quality_score = 0.0

        for req_id in required_universal + required_type_specific:
            value = answers.get(req_id)
            if _is_answer_provided(value):
                quality_score += 1
                if isinstance(value, str) and len(value.strip()) > 50:
                    quality_score += 0.5

        if total_required:
            quality_score = min(quality_score / total_required, 1.0)
        else:
            quality_score = 1.0

        answered_non_empty = sum(
            1 for question_id in all_expected if _is_answer_provided(answers.get(question_id))
        )
        completeness = (
            answered_non_empty / len(all_expected) if all_expected else 1.0
        )

        return {
            "valid": not missing,
            "missing_required": missing,
            "quality_score": quality_score,
            "completeness": completeness,
        }

    def get_follow_up_questions(
        self, answers: Dict[str, Any], user_type: str
    ) -> List[Dict[str, Any]]:
        """Generate intelligent follow-up prompts based on context."""
        follow_ups: List[Dict[str, Any]] = []
        marketing_activity = answers.get("current_marketing")
        if self._contains_option(marketing_activity, "None/very little"):
            follow_ups.append(
                {
                    "id": "why_no_marketing",
                    "text": "What's prevented you from doing marketing so far?",
                    "type": "text",
                }
            )

        if str(answers.get("primary_goal", "")).strip() == "Expand to new markets":
            follow_ups.append(
                {
                    "id": "expansion_regions",
                    "text": "Which regions or audiences are you targeting for expansion?",
                    "type": "text",
                }
            )

        if self._contains_option(answers.get("marketing_budget"), "$10K-$25K") or self._contains_option(answers.get("marketing_budget"), "$25K+"):
            follow_ups.append(
                {
                    "id": "budget_expectations",
                    "text": "What ROI or outcomes do you need to justify that spend?",
                    "type": "text",
                }
            )

        if user_type == "content_creator" and _is_answer_provided(answers.get("brand_partnerships")):
            follow_ups.append(
                {
                    "id": "dream_brands",
                    "text": "Which dream brands or collaborations are on your radar next?",
                    "type": "text",
                }
            )

        if user_type == "b2b_saas" and self._contains_option(
            answers.get("sales_motion"), "Outbound sales"
        ):
            follow_ups.append(
                {
                    "id": "outbound_stack",
                    "text": "What tooling or playbooks power your outbound motion today?",
                    "type": "text",
                }
            )

        if user_type == "agency_owner" and self._contains_option(
            answers.get("client_acquisition"), "Outbound sales"
        ):
            follow_ups.append(
                {
                    "id": "sales_team_size",
                    "text": "How is your sales team structured to support outbound?",
                    "type": "text",
                }
            )

        if user_type == "coach_educator" and _is_answer_provided(answers.get("student_results")):
            follow_ups.append(
                {
                    "id": "proof_assets",
                    "text": "Do you have testimonials or case studies we can highlight?",
                    "type": "multiple_choice",
                    "options": [
                        "Written testimonials",
                        "Video testimonials",
                        "Case studies",
                        "Before/after data",
                        "Working on it",
                    ],
                }
            )

        return follow_ups

    @staticmethod
    def _contains_option(answer: Any, option: str) -> bool:
        if isinstance(answer, str):
            return answer == option
        if isinstance(answer, Iterable) and not isinstance(answer, (str, bytes)):
            return option in answer
        return False

