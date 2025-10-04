"""Classify respondents into business archetypes."""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class BusinessType:
    label: str
    description: str
    framework: str


class BusinessTypeClassifier:
    """Return high-level business type metadata for questionnaire routing."""

    USER_TYPES: Dict[str, BusinessType] = {
        "business_owner": BusinessType(
            label="Business Owner",
            description="Own an established business (2+ years)",
            framework="ADAPT",
        ),
        "startup_founder": BusinessType(
            label="Startup Founder",
            description="Early-stage startup (0-2 years)",
            framework="Switch 6",
        ),
        "personal_brand": BusinessType(
            label="Personal Brand",
            description="Individual building personal brand/influence",
            framework="Switch 6",
        ),
        "nonprofit_leader": BusinessType(
            label="Nonprofit Leader",
            description="Running nonprofit/social impact organization",
            framework="ADAPT",
        ),
        "freelancer": BusinessType(
            label="Freelancer/Consultant",
            description="Independent service provider",
            framework="Switch 6",
        ),
        "agency_owner": BusinessType(
            label="Agency Owner",
            description="Marketing/creative/service agency",
            framework="ADAPT",
        ),
        "corporate_marketer": BusinessType(
            label="Corporate Marketer",
            description="Marketing professional at established company",
            framework="ADAPT",
        ),
        "content_creator": BusinessType(
            label="Content Creator",
            description="YouTube/TikTok/Instagram creator",
            framework="Switch 6",
        ),
        "ecommerce_owner": BusinessType(
            label="E-commerce Owner",
            description="Online store/product business",
            framework="Switch 6",
        ),
        "b2b_saas": BusinessType(
            label="B2B SaaS",
            description="Software as a Service business",
            framework="ADAPT",
        ),
        "local_business": BusinessType(
            label="Local Business",
            description="Location-dependent business",
            framework="ADAPT",
        ),
        "coach_educator": BusinessType(
            label="Coach/Educator",
            description="Teaching, training, coaching services",
            framework="Switch 6",
        ),
    }

    def get_classification_questions(self) -> List[Dict[str, object]]:
        """Return the initial question block that determines the path."""
        return [
            {
                "id": "user_type",
                "text": "What best describes you?",
                "type": "single_choice",
                "options": [
                    {
                        "value": key,
                        "label": data.label,
                        "description": data.description,
                    }
                    for key, data in self.USER_TYPES.items()
                ],
                "required": True,
            }
        ]

    def classify(self, answers: Dict[str, str]) -> Dict[str, str]:
        """Return metadata for the chosen business type."""
        user_type = answers.get("user_type")
        if user_type in self.USER_TYPES:
            payload = self.USER_TYPES[user_type]
            return {
                "business_type": user_type,
                "framework": payload.framework,
                "label": payload.label,
            }
        return {"business_type": "unknown", "framework": "ADAPT", "label": "Unknown"}

