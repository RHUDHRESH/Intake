"""Comprehensive tests for Switch 6 graph and integration layer."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from graphs.switch6_graph import (
    Switch6State,
    Switch6Dependencies,
    CircuitBreaker,
    build_switch6_graph,
    compile_switch6_graph,
    run_switch6_workflow,
)

from core.switch6_integration import (
    IntakeHandoffValidator,
    PersonaConfigManager,
    AdaptiveQuestionIntegrator,
    Switch6IntegrationOrchestrator,
    execute_switch6_from_intake,
)

from frameworks.switch6_engine import Switch6FrameworkEngine


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        # Should allow execution when closed
        assert cb.can_execute() == True
        assert cb.state == "closed"

        # Record success should keep it closed
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opening after failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)

        # Record failures to open circuit
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.failure_count == 1

        cb.record_failure()
        assert cb.state == "open"
        assert cb.failure_count == 2

        # Should not allow execution when open
        assert cb.can_execute() == False

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery to half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)  # 1 second timeout

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() == False

        # Wait for recovery timeout (simulate with direct time manipulation)
        cb.last_failure_time = 0  # Set old timestamp

        # Should transition to half-open and allow execution
        assert cb.can_execute() == True
        assert cb.state == "half-open"


class TestSwitch6Graph:
    """Test Switch 6 graph functionality."""

    @pytest.fixture
    def sample_business_data(self):
        """Sample business data for testing."""
        return {
            "user_type": "business_owner",
            "primary_goal": "Generate more leads",
            "what_you_do": "We help small restaurants increase customer footfall through social media marketing",
            "target_customer": "Local restaurant owners aged 30-50 who are tech-savvy but lack marketing expertise",
            "main_challenge": "Converting social media engagement into actual customer visits",
            "business_industry": "Digital Marketing for Restaurants",
            "annual_revenue": "$200K-$500K",
            "competitors": "Local agencies, DIY marketing tools",
            "base_price": 2500,
            "customer_acquisition_cost": 300,
        }

    @pytest.fixture
    def mock_switch6_engine(self):
        """Mock Switch 6 engine for testing."""
        engine = MagicMock(spec=Switch6FrameworkEngine)

        # Mock stage results
        engine._segment.return_value = {
            "stage": "Segment",
            "prospect_count": 25,
            "csv_file": "data/switch6_segment.csv",
            "research_confidence": 0.85,
        }

        engine._wound.return_value = {
            "stage": "Wound",
            "pain_points": [
                {
                    "label": "customer acquisition",
                    "frequency": 0.8,
                    "impact": 0.7,
                    "composite_score": 0.75,
                }
            ],
            "research_confidence": 0.82,
        }

        engine._reframe.return_value = {
            "stage": "Reframe",
            "reframe_statements": [
                {
                    "statement": "What if customer acquisition was the clearest signal that social media marketing unlocks restaurant success?",
                    "creativity": 0.8,
                    "clarity": 0.9,
                    "composite": 0.85,
                }
            ],
            "research_confidence": 0.78,
        }

        engine._offer.return_value = {
            "stage": "Offer",
            "tiers": [
                {
                    "name": "Bronze",
                    "price": 2000,
                    "deliverables": ["Strategy workshop", "Quickstart playbook"],
                    "estimated_margin": 0.65,
                }
            ],
            "research_confidence": 0.88,
        }

        engine._action.return_value = {
            "stage": "Action",
            "cta_variants": [
                {
                    "variant": "A",
                    "text": "Schedule a 20-minute road-mapping call",
                    "expected_ctr": 0.04,
                }
            ],
            "research_confidence": 0.75,
        }

        engine._cash.return_value = {
            "stage": "Cash",
            "payment_links": {"stripe": [], "paypal": []},
            "revenue_projection_csv": "data/switch6_revenue_projection.csv",
            "research_confidence": 0.80,
        }

        return engine

    def test_switch6_dependencies_creation(self, mock_switch6_engine):
        """Test Switch 6 dependencies creation."""
        deps = Switch6Dependencies(switch6_engine=mock_switch6_engine)

        assert deps.switch6_engine == mock_switch6_engine
        assert len(deps.circuit_breakers) == 6  # One for each stage
        assert "segment" in deps.circuit_breakers
        assert "wound" in deps.circuit_breakers

        # Check timeout settings
        assert deps.stage_timeouts["segment"] == 120
        assert deps.stage_timeouts["cash"] == 90

    @pytest.mark.asyncio
    async def test_switch6_workflow_execution(self, sample_business_data, mock_switch6_engine):
        """Test complete Switch 6 workflow execution."""
        deps = Switch6Dependencies(switch6_engine=mock_switch6_engine)

        results = await run_switch6_workflow(
            business_data=sample_business_data,
            user_type="business_owner",
            dependencies=deps,
        )

        assert results["framework"] == "Switch 6"
        assert results["user_type"] == "business_owner"
        assert results["execution_complete"] == True
        assert "stages" in results
        assert "segment" in results["stages"]
        assert "wound" in results["stages"]
        assert "reframe" in results["stages"]
        assert "offer" in results["stages"]
        assert "action" in results["stages"]
        assert "cash" in results["stages"]

        # Verify engine methods were called
        mock_switch6_engine._segment.assert_called_once()
        mock_switch6_engine._wound.assert_called_once()
        mock_switch6_engine._reframe.assert_called_once()
        mock_switch6_engine._offer.assert_called_once()
        mock_switch6_engine._action.assert_called_once()
        mock_switch6_engine._cash.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch6_workflow_with_failures(self, sample_business_data):
        """Test Switch 6 workflow with simulated failures."""
        # Create engine that raises exceptions
        failing_engine = MagicMock(spec=Switch6FrameworkEngine)
        failing_engine._segment.side_effect = Exception("Segment stage failed")

        deps = Switch6Dependencies(switch6_engine=failing_engine)

        results = await run_switch6_workflow(
            business_data=sample_business_data,
            user_type="business_owner",
            dependencies=deps,
        )

        assert results["framework"] == "Switch 6"
        assert results["execution_complete"] == False
        assert results["execution_complete"] == False
        assert len(results.get("errors", [])) > 0
        assert len(results.get("errors", [])) > 0


class TestIntakeHandoffValidator:
    """Test intake handoff validation."""

    @pytest.fixture
    def validator(self):
        return IntakeHandoffValidator()

    def test_valid_handoff_data(self, validator):
        """Test validation with complete data."""
        valid_data = {
            "user_type": "business_owner",
            "primary_goal": "Generate more leads and increase revenue",
            "what_you_do": "We provide comprehensive digital marketing services",
            "target_customer": "Small to medium businesses in the service industry",
            "main_challenge": "Standing out from competitors and generating consistent leads",
        }

        is_valid, errors = validator.validate_handoff_data(valid_data, "business_owner")

        assert is_valid == True
        assert len(errors) == 0

    def test_invalid_handoff_data(self, validator):
        """Test validation with incomplete data."""
        invalid_data = {
            "user_type": "business_owner",
            "primary_goal": "More leads",  # Too brief
            # Missing other required fields
        }

        is_valid, errors = validator.validate_handoff_data(invalid_data, "business_owner")

        assert is_valid == False
        assert len(errors) > 0
        assert any("Missing required field" in error for error in errors)

    def test_unsupported_user_type(self, validator):
        """Test validation with unsupported user type."""
        data = {
            "user_type": "individual",
            "primary_goal": "Generate more leads",
            "what_you_do": "Something",
            "target_customer": "Someone",
            "main_challenge": "Something",
        }

        is_valid, errors = validator.validate_handoff_data(data, "individual")

        assert is_valid == False
        assert any("not supported by Switch 6" in error for error in errors)

    def test_data_quality_assessment(self, validator):
        """Test data quality scoring."""
        # High quality data
        high_quality_data = {
            "user_type": "business_owner",
            "primary_goal": "Generate more leads and establish ourselves as the premier digital marketing agency for restaurants in the Chennai area",
            "what_you_do": "We provide comprehensive digital marketing services including social media management, content creation, and lead generation",
            "target_customer": "Restaurant owners and managers aged 30-55 who understand the value of digital marketing but lack the time or expertise",
            "main_challenge": "Differentiating our services from competitors and demonstrating clear ROI to potential clients",
        }

        quality_score = validator._assess_data_quality(high_quality_data)
        assert quality_score >= 0.8  # Should be high quality

        # Low quality data
        low_quality_data = {
            "user_type": "business_owner",
            "primary_goal": "Leads",
            "what_you_do": "Marketing",
            "target_customer": "People",
            "main_challenge": "Hard",
        }

        quality_score = validator._assess_data_quality(low_quality_data)
        assert quality_score < 0.7  # Should be low quality


class TestPersonaConfigManager:
    """Test persona configuration management."""

    @pytest.fixture
    def persona_manager(self):
        return PersonaConfigManager()

    def test_get_persona_config(self, persona_manager):
        """Test getting persona configuration."""
        business_owner_config = persona_manager.get_persona_config("business_owner")
        startup_founder_config = persona_manager.get_persona_config("startup_founder")
        personal_brand_config = persona_manager.get_persona_config("personal_brand")

        # Each should have the expected structure
        for config in [business_owner_config, startup_founder_config, personal_brand_config]:
            assert "segment_keywords" in config
            assert "wound_focus" in config
            assert "reframe_emphasis" in config
            assert "offer_structure" in config
            assert "action_priority" in config
            assert "cash_metrics" in config

        # Should be different for different personas
        assert business_owner_config["segment_keywords"] != startup_founder_config["segment_keywords"]

    def test_adapt_business_data(self, persona_manager):
        """Test adapting business data for persona."""
        intake_data = {
            "user_type": "business_owner",
            "business_industry": "Digital Marketing",
            "primary_goal": "Generate more leads",
        }

        adapted_data = persona_manager.adapt_business_data(intake_data, "business_owner")

        assert "persona_config" in adapted_data
        assert "enhanced_keywords" in adapted_data
        assert "stage_focus" in adapted_data

        # Should include original data plus enhancements
        assert adapted_data["user_type"] == "business_owner"
        assert adapted_data["business_industry"] == "Digital Marketing"
        assert "industry" in adapted_data["enhanced_keywords"]


class TestAdaptiveQuestionIntegrator:
    """Test adaptive question integration."""

    @pytest.fixture
    def question_integrator(self):
        return AdaptiveQuestionIntegrator()

    def test_switch6_specific_questions(self, question_integrator):
        """Test generation of Switch 6 specific questions."""
        current_data = {
            "user_type": "business_owner",
            "primary_goal": "Generate leads",
            # Missing industry, competitors, pricing info
        }

        questions = question_integrator.get_switch6_specific_questions("business_owner", current_data)

        # Should generate questions for missing data
        question_ids = [q["id"] for q in questions]
        assert "business_industry" in question_ids
        assert "competitors" in question_ids
        assert "base_price" in question_ids

        # Questions should have proper structure
        for question in questions:
            assert "id" in question
            assert "question" in question
            assert "type" in question
            assert "category" in question

    def test_merge_adaptive_responses(self, question_integrator):
        """Test merging adaptive question responses."""
        original_data = {
            "user_type": "business_owner",
            "primary_goal": "Generate leads",
            "adaptive_questions_asked": 2,
        }

        new_responses = {
            "business_industry": "Digital Marketing",
            "base_price": 2500,
        }

        merged = question_integrator.merge_adaptive_responses(original_data, new_responses)

        # Should include original data
        assert merged["user_type"] == "business_owner"
        assert merged["primary_goal"] == "Generate leads"

        # Should include new responses
        assert merged["business_industry"] == "Digital Marketing"
        assert merged["base_price"] == 2500

        # Should update tracking
        assert merged["adaptive_questions_asked"] == 4  # 2 + 2 new
        assert "last_adaptive_update" in merged


class TestSwitch6IntegrationOrchestrator:
    """Test the main integration orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        return Switch6IntegrationOrchestrator()

    @pytest.mark.asyncio
    async def test_successful_handoff(self, orchestrator):
        """Test successful handoff from intake to Switch 6."""
        # Mock the Switch 6 workflow to return success
        with patch('core.switch6_integration.run_switch6_workflow') as mock_workflow:
            mock_workflow.return_value = {
                "framework": "Switch 6",
                "execution_complete": True,
                "framework_completion_score": 0.85,
                "stages": {
                    "segment": {"stage": "Segment"},
                    "wound": {"stage": "Wound"},
                    "reframe": {"stage": "Reframe"},
                    "offer": {"stage": "Offer"},
                    "action": {"stage": "Action"},
                    "cash": {"stage": "Cash"},
                },
                "errors": [],
            }

            intake_state = {
                "answers": {
                    "user_type": "business_owner",
                    "primary_goal": "Generate more qualified leads for our digital marketing agency",
                    "what_you_do": "We provide comprehensive digital marketing services including social media management, content creation, and lead generation for restaurants",
                    "target_customer": "Restaurant owners and managers aged 30-55 who understand the value of digital marketing but lack the time or expertise to execute it effectively",
                    "main_challenge": "Standing out from competitors and demonstrating clear ROI to potential clients in a crowded market",
                    "business_industry": "Digital Marketing for Restaurants",
                },
                "user_type": "business_owner",
                "classification": {"business_type": "business_owner"},
            }

            result = await orchestrator.orchestrate_handoff(intake_state)

            assert result["success"] == True
            assert result["intake_handoff"]["validation_passed"] == True
            assert result["intake_handoff"]["persona_config_applied"] == True
            assert result["switch6_results"]["execution_complete"] == True
            assert result["framework_completion_score"] == 0.85

    @pytest.mark.asyncio
    async def test_handoff_with_insufficient_data(self, orchestrator):
        """Test handoff when intake data is insufficient."""
        intake_state = {
            "answers": {
                "user_type": "business_owner",
                "primary_goal": "Leads",  # Too brief
                # Missing other required fields
            },
            "user_type": "business_owner",
        }

        result = await orchestrator.orchestrate_handoff(intake_state)

        assert result["success"] == False
        assert result["stage"] == "validation"
        assert result["needs_adaptive_questions"] == True
        assert "adaptive_questions" in result
        assert len(result["adaptive_questions"]) > 0

    def test_can_proceed_to_switch6(self, orchestrator):
        """Test checking if we can proceed to Switch 6."""
        # Valid data
        valid_intake = {
            "answers": {
                "user_type": "business_owner",
                "primary_goal": "Generate more qualified leads",
                "what_you_do": "Digital marketing services",
                "target_customer": "Restaurant owners",
                "main_challenge": "Competition and ROI demonstration",
            },
            "user_type": "business_owner",
        }

        can_proceed, reason = orchestrator.can_proceed_to_switch6(valid_intake)
        assert can_proceed == True
        assert reason == "Ready for Switch 6 execution"

        # Invalid data
        invalid_intake = {
            "answers": {
                "user_type": "business_owner",
                "primary_goal": "Leads",  # Too brief
            },
            "user_type": "business_owner",
        }

        can_proceed, reason = orchestrator.can_proceed_to_switch6(invalid_intake)
        assert can_proceed == False
        assert "Validation failed" in reason


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    @pytest.mark.asyncio
    async def test_execute_switch6_from_intake_success(self):
        """Test successful end-to-end execution."""
        # Mock the workflow execution
        with patch('core.switch6_integration.run_switch6_workflow') as mock_workflow:
            mock_workflow.return_value = {
                "framework": "Switch 6",
                "execution_complete": True,
                "framework_completion_score": 0.82,
                "stages": {"segment": {}, "wound": {}, "reframe": {}, "offer": {}, "action": {}, "cash": {}},
                "errors": [],
            }

            intake_state = {
                "answers": {
                    "user_type": "business_owner",
                    "primary_goal": "Generate more qualified leads for our restaurant marketing agency",
                    "what_you_do": "We help restaurants increase their customer base through targeted social media marketing and local SEO strategies",
                    "target_customer": "Independent restaurant owners aged 35-60 who are tech-savvy but overwhelmed by digital marketing options",
                    "main_challenge": "Cutting through the noise of competing agencies and proving tangible ROI from marketing spend",
                    "business_industry": "Restaurant Marketing",
                    "annual_revenue": "$500K-$1M",
                },
                "user_type": "business_owner",
                "classification": {"business_type": "business_owner"},
            }

            result = await execute_switch6_from_intake(intake_state)

            assert result["success"] == True
            assert result["switch6_results"]["execution_complete"] == True
            assert result["framework_completion_score"] == 0.82

    @pytest.mark.asyncio
    async def test_execute_switch6_from_intake_needs_more_data(self):
        """Test execution when more data is needed."""
        intake_state = {
            "answers": {
                "user_type": "business_owner",
                "primary_goal": "More leads",  # Insufficient detail
            },
            "user_type": "business_owner",
        }

        result = await execute_switch6_from_intake(intake_state)

        assert result["success"] == False
        assert result["needs_more_data"] == True
        assert "adaptive_questions" in result
        assert len(result["adaptive_questions"]) > 0

        # Check that adaptive questions include necessary fields
        question_ids = [q["id"] for q in result["adaptive_questions"]]
        assert "business_industry" in question_ids
        assert "what_you_do" in question_ids


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
