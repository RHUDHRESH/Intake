"""
Enhanced Position Validator Engine with pluggable modules and dual-mode operation.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol
from datetime import datetime
from enum import Enum

from ..core.retry import RetryPolicy, with_retry
from ..core.mixins import ConfigurableMixin
from ..market_research.resilience import CircuitBreaker, BulkheadExecutor

logger = logging.getLogger(__name__)

class ValidationMode(str, Enum):
    """Validation modes for position scoring."""
    LOCAL_HEURISTICS = "local_heuristics"
    LLM_POWERED = "llm_powered"
    HYBRID = "hybrid"

class SeverityLevel(str, Enum):
    """Severity levels for feedback."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"

@dataclass
class ValidationFeedback:
    """Structured feedback from validation modules."""
    message: str
    severity: SeverityLevel
    module: str
    category: str
    suggestion: Optional[str] = None
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)

@dataclass
class ModuleConfig:
    """Configuration for validation modules."""
    name: str
    weight: float = 1.0
    enabled: bool = True
    mode: ValidationMode = ValidationMode.HYBRID
    timeout_seconds: int = 30
    retry_policy: Optional[RetryPolicy] = None

class PositionScoringModule(Protocol):
    """Protocol for position scoring modules."""

    name: str

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score a positioning statement and return detailed results."""
        ...

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate a statement and return feedback."""
        ...

    def is_available(self) -> bool:
        """Check if this module is available for use."""
        ...

class ADAPTPositionModule:
    """ADAPT framework position validation module."""

    name = "adapt"

    def __init__(self):
        self.framework_keywords = {
            "audience": ["target", "customer", "user", "client", "buyer"],
            "desire": ["want", "need", "desire", "crave", "seek"],
            "aspire": ["dream", "vision", "goal", "ambition", "aim"],
            "problem": ["problem", "challenge", "issue", "pain", "struggle"],
            "transform": ["transform", "change", "become", "evolve", "shift"]
        }

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score using ADAPT framework criteria."""
        statement_lower = statement.lower()
        scores = {}

        # Check for each ADAPT component
        for component, keywords in self.framework_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in statement_lower)
            coverage = min(matches / len(keywords), 1.0)
            scores[component] = round(coverage, 3)

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        return {
            "module": self.name,
            "score": round(overall_score, 3),
            "component_scores": scores,
            "framework": "ADAPT",
            "feedback": self.validate(statement, context=context)
        }

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate ADAPT positioning statement."""
        feedback = []
        statement_lower = statement.lower()

        # Check for missing components
        missing_components = []
        for component, keywords in self.framework_keywords.items():
            if not any(keyword in statement_lower for keyword in keywords):
                missing_components.append(component)

        if missing_components:
            feedback.append(ValidationFeedback(
                message=f"Missing ADAPT components: {', '.join(missing_components)}",
                severity=SeverityLevel.WARNING,
                module=self.name,
                category="completeness",
                suggestion=f"Include references to: {', '.join(missing_components)}",
                confidence=0.8
            ))

        # Check statement length
        if len(statement) < 50:
            feedback.append(ValidationFeedback(
                message="Positioning statement is too short",
                severity=SeverityLevel.INFO,
                module=self.name,
                category="length",
                suggestion="Expand to 50+ characters for better clarity",
                confidence=0.7
            ))

        return feedback

    def is_available(self) -> bool:
        return True

class Switch6PositionModule:
    """Switch 6 framework position validation module."""

    name = "switch6"

    def __init__(self):
        self.switch6_keywords = {
            "segment": ["segment", "audience", "target", "niche", "market"],
            "wound": ["pain", "problem", "challenge", "frustration", "issue"],
            "reframe": ["reframe", "shift", "perspective", "view", "angle"],
            "offer": ["offer", "solution", "product", "service", "value"],
            "action": ["action", "cta", "call", "next", "step"],
            "cash": ["revenue", "profit", "money", "return", "roi"]
        }

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score using Switch 6 framework criteria."""
        statement_lower = statement.lower()
        scores = {}

        # Check for each Switch 6 stage
        for stage, keywords in self.switch6_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in statement_lower)
            coverage = min(matches / len(keywords), 1.0)
            scores[stage] = round(coverage, 3)

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        return {
            "module": self.name,
            "score": round(overall_score, 3),
            "stage_scores": scores,
            "framework": "Switch6",
            "feedback": self.validate(statement, context=context)
        }

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate Switch 6 positioning statement."""
        feedback = []
        statement_lower = statement.lower()

        # Check for business model clarity
        business_indicators = ["saas", "service", "product", "platform", "solution"]
        if not any(indicator in statement_lower for indicator in business_indicators):
            feedback.append(ValidationFeedback(
                message="Business model not clearly indicated",
                severity=SeverityLevel.INFO,
                module=self.name,
                category="clarity",
                suggestion="Specify if this is a SaaS product, service, platform, etc.",
                confidence=0.6
            ))

        # Check for monetization hint
        monetization_indicators = ["revenue", "pricing", "cost", "value", "roi"]
        if not any(indicator in statement_lower for indicator in monetization_indicators):
            feedback.append(ValidationFeedback(
                message="Monetization path not clear",
                severity=SeverityLevel.SUGGESTION,
                module=self.name,
                category="monetization",
                suggestion="Include how this creates revenue or value",
                confidence=0.5
            ))

        return feedback

    def is_available(self) -> bool:
        return True

class OgilvyPositionModule:
    """Ogilvy Big Idea framework position validation module."""

    name = "ogilvy"

    def __init__(self):
        self.big_idea_indicators = [
            "disruptive", "revolutionary", "breakthrough", "game-changing",
            "transformative", "innovative", "unique", "first", "only"
        ]

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score using Ogilvy Big Idea criteria."""
        statement_lower = statement.lower()
        scores = {}

        # Check for big idea characteristics
        innovation_score = sum(1 for indicator in self.big_idea_indicators if indicator in statement_lower)
        scores["innovation"] = round(min(innovation_score / 3, 1.0), 3)

        # Check for memorability (simplicity + impact)
        word_count = len(statement.split())
        simplicity_score = 1.0 if word_count <= 15 else max(0.3, 1.0 - (word_count - 15) * 0.05)
        scores["simplicity"] = round(simplicity_score, 3)

        # Check for benefit focus
        benefit_indicators = ["better", "faster", "easier", "more", "less", "save", "increase", "reduce"]
        benefit_score = sum(1 for indicator in benefit_indicators if indicator in statement_lower)
        scores["benefit_focus"] = round(min(benefit_score / 3, 1.0), 3)

        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        return {
            "module": self.name,
            "score": round(overall_score, 3),
            "criteria_scores": scores,
            "framework": "Ogilvy",
            "feedback": self.validate(statement, context=context)
        }

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate Ogilvy Big Idea positioning."""
        feedback = []
        statement_lower = statement.lower()

        # Check for brand personality
        if not any(char in statement_lower for char in ["!", "?", "—", ":", "–"]):
            feedback.append(ValidationFeedback(
                message="Lacks personality or emotional punch",
                severity=SeverityLevel.SUGGESTION,
                module=self.name,
                category="personality",
                suggestion="Add emotional language or punctuation for impact",
                confidence=0.6
            ))

        # Check for specificity
        generic_terms = ["good", "great", "nice", "better", "best"]
        if any(term in statement_lower for term in generic_terms):
            feedback.append(ValidationFeedback(
                message="Contains generic or vague terms",
                severity=SeverityLevel.WARNING,
                module=self.name,
                category="specificity",
                suggestion="Replace generic terms with specific, measurable benefits",
                confidence=0.8
            ))

        return feedback

    def is_available(self) -> bool:
        return True

class GodinPositionModule:
    """Seth Godin framework position validation module."""

    name = "godin"

    def __init__(self):
        self.godin_indicators = {
            "remarkable": ["remarkable", "worth", "talk", "share", "spread", "viral"],
            "purple_cow": ["different", "unique", "standout", "noticeable", "obvious"],
            "permission": ["permission", "opt-in", "subscribe", "follow", "join"],
            "tribe": ["community", "group", "tribe", "movement", "followers"]
        }

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score using Seth Godin framework criteria."""
        statement_lower = statement.lower()
        scores = {}

        # Check for each Godin concept
        for concept, keywords in self.godin_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in statement_lower)
            coverage = min(matches / len(keywords), 1.0)
            scores[concept] = round(coverage, 3)

        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        return {
            "module": self.name,
            "score": round(overall_score, 3),
            "concept_scores": scores,
            "framework": "Godin",
            "feedback": self.validate(statement, context=context)
        }

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate Godin positioning statement."""
        feedback = []
        statement_lower = statement.lower()

        # Check for remarkability
        if not any(indicator in statement_lower for indicator in self.godin_indicators["remarkable"]):
            feedback.append(ValidationFeedback(
                message="Not clearly remarkable or noteworthy",
                severity=SeverityLevel.CRITICAL,
                module=self.name,
                category="remarkability",
                suggestion="Make it remarkable - something worth talking about",
                confidence=0.9
            ))

        # Check for permission marketing alignment
        if not any(indicator in statement_lower for indicator in self.godin_indicators["permission"]):
            feedback.append(ValidationFeedback(
                message="Missing permission marketing elements",
                severity=SeverityLevel.INFO,
                module=self.name,
                category="permission",
                suggestion="Consider how this builds permission-based relationships",
                confidence=0.5
            ))

        return feedback

    def is_available(self) -> bool:
        return True

class HybridPositionModule:
    """Hybrid validation combining multiple frameworks."""

    name = "hybrid"

    def __init__(self, modules: List[PositionScoringModule]):
        self.modules = modules

    def score(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Score using hybrid approach combining multiple frameworks."""
        hybrid_scores = {}
        all_feedback = []

        # Get scores from all available modules
        for module in self.modules:
            if module.is_available():
                try:
                    result = module.score(statement, context=context)
                    hybrid_scores[module.name] = result.get("score", 0.0)
                    all_feedback.extend(result.get("feedback", []))
                except Exception as e:
                    logger.warning(f"Module {module.name} failed: {str(e)}")
                    hybrid_scores[module.name] = 0.0

        # Calculate hybrid score (weighted average)
        if hybrid_scores:
            # Weight more recent frameworks higher
            weights = {"adapt": 0.2, "switch6": 0.3, "ogilvy": 0.25, "godin": 0.25}
            weighted_sum = sum(
                score * weights.get(module_name, 0.2)
                for module_name, score in hybrid_scores.items()
            )
            total_weight = sum(weights.get(name, 0.2) for name in hybrid_scores.keys())
            hybrid_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        else:
            hybrid_score = 0.0

        return {
            "module": self.name,
            "score": round(hybrid_score, 3),
            "framework_scores": hybrid_scores,
            "framework": "Hybrid",
            "feedback": all_feedback
        }

    def validate(self, statement: str, *, context: Optional[Dict[str, Any]] = None) -> List[ValidationFeedback]:
        """Validate using hybrid approach."""
        all_feedback = []

        for module in self.modules:
            if module.is_available():
                try:
                    feedback = module.validate(statement, context=context)
                    all_feedback.extend(feedback)
                except Exception as e:
                    logger.warning(f"Module {module.name} validation failed: {str(e)}")

        return all_feedback

    def is_available(self) -> bool:
        return len([m for m in self.modules if m.is_available()]) > 0

class EnhancedPositionValidatorEngine(ConfigurableMixin):
    """Enhanced position validator with pluggable modules and dual-mode operation."""

    def __init__(
        self,
        modules: Optional[Iterable[PositionScoringModule]] = None,
        default_mode: ValidationMode = ValidationMode.HYBRID,
        auto_weighting: bool = True
    ):
        """Initialize enhanced position validator engine."""
        super().__init__()

        # Initialize default modules if none provided
        if modules is None:
            modules = [
                ADAPTPositionModule(),
                Switch6PositionModule(),
                OgilvyPositionModule(),
                GodinPositionModule(),
                HybridPositionModule([
                    ADAPTPositionModule(),
                    Switch6PositionModule(),
                    OgilvyPositionModule(),
                    GodinPositionModule()
                ])
            ]

        self._modules = {module.name: module for module in modules}
        self.default_mode = default_mode
        self.auto_weighting = auto_weighting

        # Resilience components
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        self.bulkhead = BulkheadExecutor(max_concurrency=5)

        logger.info(f"EnhancedPositionValidatorEngine initialized with {len(self._modules)} modules")

    def score(
        self,
        statement: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        module_overrides: Optional[Dict[str, ModuleConfig]] = None,
        mode: Optional[ValidationMode] = None
    ) -> Dict[str, Any]:
        """
        Score positioning statement with enhanced validation and feedback.

        Args:
            statement: The positioning statement to validate
            context: Additional context for validation
            module_overrides: Override module configurations
            mode: Validation mode to use

        Returns:
            Comprehensive validation results with scores and feedback
        """
        context = context or {}
        overrides = module_overrides or {}
        mode = mode or self.default_mode

        # Execute scoring with circuit breaker protection
        async def _score_statement():
            return await self._execute_scoring(statement, context, overrides, mode)

        try:
            return self.circuit_breaker.run(_score_statement)
        except Exception as e:
            logger.error(f"Position scoring failed: {str(e)}")
            return {
                "statement": statement,
                "score": 0.0,
                "error": str(e),
                "module_results": [],
                "feedback": [ValidationFeedback(
                    message=f"Validation failed: {str(e)}",
                    severity=SeverityLevel.CRITICAL,
                    module="engine",
                    category="error",
                    confidence=1.0
                )]
            }

    async def _execute_scoring(
        self,
        statement: str,
        context: Dict[str, Any],
        overrides: Dict[str, ModuleConfig],
        mode: ValidationMode
    ) -> Dict[str, Any]:
        """Execute scoring with bulkhead protection."""
        async def _scoring_pipeline():
            results = []
            total_weight = 0.0
            weighted_score = 0.0

            # Score with each enabled module
            for name, module in self._modules.items():
                if not module.is_available():
                    continue

                cfg = overrides.get(name, ModuleConfig(name=name))
                if not cfg.enabled:
                    continue

                # Execute module scoring with timeout protection
                try:
                    async def _score_with_module():
                        return module.score(statement, context=context)

                    # Apply timeout if configured
                    if cfg.timeout_seconds > 0:
                        result = await asyncio.wait_for(
                            _score_with_module(),
                            timeout=cfg.timeout_seconds
                        )
                    else:
                        result = await _score_with_module()

                    # Apply module weight
                    weight = cfg.weight
                    result["weight"] = weight
                    results.append(result)

                    # Calculate weighted score
                    module_score = result.get("score", 0.0)
                    total_weight += weight
                    weighted_score += module_score * weight

                except asyncio.TimeoutError:
                    logger.warning(f"Module {name} timed out after {cfg.timeout_seconds}s")
                    results.append({
                        "module": name,
                        "score": 0.0,
                        "error": "timeout",
                        "weight": cfg.weight
                    })
                except Exception as e:
                    logger.warning(f"Module {name} failed: {str(e)}")
                    results.append({
                        "module": name,
                        "score": 0.0,
                        "error": str(e),
                        "weight": cfg.weight
                    })

            # Calculate final scores
            aggregate_score = weighted_score / total_weight if total_weight > 0 else 0.0

            # Collect all feedback
            all_feedback = []
            for result in results:
                feedback_list = result.get("feedback", [])
                if feedback_list:
                    all_feedback.extend(feedback_list)

            # Auto-weighting if enabled
            if self.auto_weighting and total_weight > 0:
                results = self._apply_auto_weighting(results, context)

            return {
                "statement": statement,
                "score": round(aggregate_score, 3),
                "confidence": self._calculate_confidence(results),
                "mode": mode.value,
                "module_results": results,
                "feedback": all_feedback,
                "validation_timestamp": datetime.now().isoformat(),
                "modules_used": len([r for r in results if "error" not in r])
            }

        return await self.bulkhead.run(_scoring_pipeline)

    def _apply_auto_weighting(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply auto-weighting based on context and performance."""
        if not results:
            return results

        # Base weights by framework recency/relevance
        framework_weights = {
            "hybrid": 1.2,    # Most comprehensive
            "switch6": 1.1,   # Most recent
            "adapt": 1.0,     # Original
            "ogilvy": 0.9,    # Classic but still relevant
            "godin": 0.9      # Classic but still relevant
        }

        for result in results:
            module_name = result.get("module", "")
            base_weight = result.get("weight", 1.0)

            # Apply framework-based weighting
            framework_multiplier = framework_weights.get(module_name, 1.0)
            new_weight = base_weight * framework_multiplier

            # Adjust based on context
            if context.get("industry") == "tech_saas":
                if module_name in ["switch6", "adapt"]:
                    new_weight *= 1.1  # Boost tech-focused frameworks

            result["auto_weight"] = round(new_weight, 3)
            result["weight"] = new_weight

        return results

    def _calculate_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence based on module agreement and availability."""
        if not results:
            return 0.0

        # Base confidence on number of successful modules
        successful_modules = len([r for r in results if "error" not in r])
        base_confidence = successful_modules / len(results)

        # Boost confidence if modules agree (low variance in scores)
        scores = [r.get("score", 0.0) for r in results if "error" not in r]
        if len(scores) > 1:
            score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            agreement_bonus = max(0, 0.2 - score_variance)
            base_confidence += agreement_bonus

        return round(min(base_confidence, 1.0), 3)

    def get_available_modules(self) -> Dict[str, bool]:
        """Get availability status of all modules."""
        return {name: module.is_available() for name, module in self._modules.items()}

    def get_module_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all modules."""
        return {
            name: {
                "available": module.is_available(),
                "framework": getattr(module, "framework", "unknown"),
                "type": "pluggable_module"
            }
            for name, module in self._modules.items()
        }

    def add_module(self, module: PositionScoringModule):
        """Add a new validation module."""
        self._modules[module.name] = module
        logger.info(f"Added validation module: {module.name}")

    def remove_module(self, module_name: str) -> bool:
        """Remove a validation module."""
        if module_name in self._modules:
            del self._modules[module_name]
            logger.info(f"Removed validation module: {module_name}")
            return True
        return False

# Convenience function to create engine with all default modules
def create_position_validator_engine() -> EnhancedPositionValidatorEngine:
    """Create position validator engine with all default modules."""
    return EnhancedPositionValidatorEngine()

# Export for backward compatibility
PositionValidatorEngine = EnhancedPositionValidatorEngine

__all__ = [
    "ValidationMode", "SeverityLevel", "ValidationFeedback", "ModuleConfig",
    "PositionScoringModule", "ADAPTPositionModule", "Switch6PositionModule",
    "OgilvyPositionModule", "GodinPositionModule", "HybridPositionModule",
    "EnhancedPositionValidatorEngine", "create_position_validator_engine"
]
