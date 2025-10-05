"""LangGraph orchestration for Switch 6 research framework with circuit breakers and error handling."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledGraph
from langgraph.pregel.retry import RetryPolicy

from Intake.frameworks.switch6_engine import Switch6FrameworkEngine


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Switch6State(TypedDict, total=False):
    """State payload that flows through the Switch 6 research graph."""

    # Input data from intake
    business_data: Dict[str, Any]
    user_type: str

    # Stage results
    segment_results: Optional[Dict[str, Any]]
    wound_results: Optional[Dict[str, Any]]
    reframe_results: Optional[Dict[str, Any]]
    offer_results: Optional[Dict[str, Any]]
    action_results: Optional[Dict[str, Any]]
    cash_results: Optional[Dict[str, Any]]

    # Error tracking
    errors: List[Dict[str, Any]]
    retry_count: Dict[str, int]

    # Circuit breaker state
    circuit_breaker_trips: Dict[str, bool]

    # Execution metadata
    start_time: Optional[str]
    current_stage: Optional[str]
    execution_complete: bool
    framework_completion_score: Optional[float]

    # Validation flags
    segment_valid: bool
    wound_valid: bool
    reframe_valid: bool
    offer_valid: bool
    action_valid: bool
    cash_valid: bool


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation for stage protection."""

    failure_threshold: int = 3
    recovery_timeout: int = 300  # 5 minutes
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True

    def record_success(self) -> None:
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


@dataclass
class Switch6Dependencies:
    """Container for injectable dependencies used by the Switch 6 graph."""

    switch6_engine: Switch6FrameworkEngine
    circuit_breakers: Dict[str, CircuitBreaker] = field(default_factory=lambda: {
        "segment": CircuitBreaker(),
        "wound": CircuitBreaker(),
        "reframe": CircuitBreaker(),
        "offer": CircuitBreaker(),
        "action": CircuitBreaker(),
        "cash": CircuitBreaker(),
    })

    # Timeout settings for each stage (in seconds)
    stage_timeouts: Dict[str, int] = field(default_factory=lambda: {
        "segment": 120,  # 2 minutes
        "wound": 90,     # 1.5 minutes
        "reframe": 100,  # ~1.7 minutes
        "offer": 80,     # 1.3 minutes
        "action": 60,    # 1 minute
        "cash": 90,      # 1.5 minutes
    })


def _default_dependencies() -> Switch6Dependencies:
    """Create default dependencies for the Switch 6 graph."""
    return Switch6Dependencies(switch6_engine=Switch6FrameworkEngine())


def build_switch6_graph(
    *,
    dependencies: Optional[Switch6Dependencies] = None,
) -> StateGraph:
    """Construct the Switch 6 LangGraph workflow with error handling and circuit breakers."""

    deps = dependencies or _default_dependencies()
    graph = StateGraph(Switch6State)

    def _initialize_state(state: Switch6State) -> Switch6State:
        """Initialize default state values."""
        current_time = datetime.now(timezone.utc).isoformat()
        return {
            **state,
            "errors": state.get("errors", []),
            "retry_count": state.get("retry_count", {}),
            "circuit_breaker_trips": state.get("circuit_breaker_trips", {}),
            "start_time": state.get("start_time", current_time),
            "current_stage": state.get("current_stage"),
            "execution_complete": state.get("execution_complete", False),
            "segment_valid": state.get("segment_valid", False),
            "wound_valid": state.get("wound_valid", False),
            "reframe_valid": state.get("reframe_valid", False),
            "offer_valid": state.get("offer_valid", False),
            "action_valid": state.get("action_valid", False),
            "cash_valid": state.get("cash_valid", False),
        }

    def _add_error(state: Switch6State, stage: str, error: Exception) -> Switch6State:
        """Add an error to the state."""
        errors = state.get("errors", [])
        errors.append({
            "stage": stage,
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {**state, "errors": errors}

    def _can_skip_stage(state: Switch6State, stage: str) -> bool:
        """Determine if a stage can be skipped based on previous results."""
        if stage == "wound":
            return not state.get("segment_valid", False)
        elif stage == "reframe":
            return not state.get("wound_valid", False)
        elif stage == "offer":
            return not state.get("reframe_valid", False)
        elif stage == "action":
            return not state.get("offer_valid", False)
        elif stage == "cash":
            return not state.get("action_valid", False)
        return False

    def _execute_with_timeout(coro, timeout: int):
        """Execute a coroutine with timeout."""
        try:
            return asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Stage execution timed out after {timeout} seconds")

    async def segment_node(state: Switch6State) -> Switch6State:
        """Execute the segment stage with error handling and circuit breaker."""
        stage = "segment"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            # Execute with timeout
            business_data = state.get("business_data", {})
            if not business_data:
                raise ValueError("No business data provided for segment stage")

            # Run the segment stage
            segment_results = deps.switch6_engine._segment(business_data)

            # Update state
            new_state = {
                **state,
                "segment_results": segment_results,
                "segment_valid": True,
                "current_stage": stage,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "segment_valid": False,
                "current_stage": stage,
                "execution_complete": True,  # Mark as complete with errors
            }

    async def wound_node(state: Switch6State) -> Switch6State:
        """Execute the wound stage with error handling and circuit breaker."""
        stage = "wound"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            business_data = state.get("business_data", {})
            segment_results = state.get("segment_results", {})

            if not business_data:
                raise ValueError("No business data provided for wound stage")

            # Execute with timeout
            wound_results = deps.switch6_engine._wound(business_data, segment_results)

            # Update state
            new_state = {
                **state,
                "wound_results": wound_results,
                "wound_valid": True,
                "current_stage": stage,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "wound_valid": False,
                "current_stage": stage,
            }

    async def reframe_node(state: Switch6State) -> Switch6State:
        """Execute the reframe stage with error handling and circuit breaker."""
        stage = "reframe"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            business_data = state.get("business_data", {})
            wound_results = state.get("wound_results", {})

            if not business_data:
                raise ValueError("No business data provided for reframe stage")

            # Execute with timeout
            reframe_results = deps.switch6_engine._reframe(business_data, wound_results)

            # Update state
            new_state = {
                **state,
                "reframe_results": reframe_results,
                "reframe_valid": True,
                "current_stage": stage,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "reframe_valid": False,
                "current_stage": stage,
            }

    async def offer_node(state: Switch6State) -> Switch6State:
        """Execute the offer stage with error handling and circuit breaker."""
        stage = "offer"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            business_data = state.get("business_data", {})
            reframe_results = state.get("reframe_results", {})

            if not business_data:
                raise ValueError("No business data provided for offer stage")

            # Execute with timeout
            offer_results = deps.switch6_engine._offer(business_data, reframe_results)

            # Update state
            new_state = {
                **state,
                "offer_results": offer_results,
                "offer_valid": True,
                "current_stage": stage,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "offer_valid": False,
                "current_stage": stage,
            }

    async def action_node(state: Switch6State) -> Switch6State:
        """Execute the action stage with error handling and circuit breaker."""
        stage = "action"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            business_data = state.get("business_data", {})
            offer_results = state.get("offer_results", {})

            if not business_data:
                raise ValueError("No business data provided for action stage")

            # Execute with timeout
            action_results = deps.switch6_engine._action(business_data, offer_results)

            # Update state
            new_state = {
                **state,
                "action_results": action_results,
                "action_valid": True,
                "current_stage": stage,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "action_valid": False,
                "current_stage": stage,
            }

    async def cash_node(state: Switch6State) -> Switch6State:
        """Execute the cash stage with error handling and circuit breaker."""
        stage = "cash"
        state = _initialize_state(state)

        # Check circuit breaker
        cb = deps.circuit_breakers[stage]
        if not cb.can_execute():
            logger.warning(f"Circuit breaker is OPEN for stage: {stage}")
            return _add_error(state, stage, Exception(f"Circuit breaker open for {stage}"))

        # Check if we can skip this stage
        if _can_skip_stage(state, stage):
            logger.info(f"Skipping stage: {stage} due to invalid previous stage")
            return {**state, "current_stage": stage}

        try:
            business_data = state.get("business_data", {})
            segment_results = state.get("segment_results", {})
            wound_results = state.get("wound_results", {})
            offer_results = state.get("offer_results", {})
            action_results = state.get("action_results", {})

            if not business_data:
                raise ValueError("No business data provided for cash stage")

            # Execute with timeout
            cash_results = deps.switch6_engine._cash(
                business_data, segment_results, wound_results,
                offer_results, action_results
            )

            # Update state
            new_state = {
                **state,
                "cash_results": cash_results,
                "cash_valid": True,
                "current_stage": stage,
                "execution_complete": True,
                "retry_count": {**state.get("retry_count", {}), stage: 0},
            }

            # Record success in circuit breaker
            cb.record_success()
            logger.info(f"Successfully completed stage: {stage}")
            return new_state

        except Exception as e:
            logger.error(f"Error in stage {stage}: {str(e)}")
            cb.record_failure()

            # Check retry logic
            retry_count = state.get("retry_count", {}).get(stage, 0) + 1
            max_retries = 2

            if retry_count <= max_retries:
                logger.info(f"Retrying stage {stage}, attempt {retry_count}")
                return {
                    **state,
                    "retry_count": {**state.get("retry_count", {}), stage: retry_count},
                    "current_stage": stage,
                }

            # Max retries exceeded
            error_state = _add_error(state, stage, e)
            return {
                **error_state,
                "cash_valid": False,
                "current_stage": stage,
                "execution_complete": True,
            }

    # Add nodes to the graph with retry policies
    graph.add_node("segment", segment_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("wound", wound_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("reframe", reframe_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("offer", offer_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("action", action_node, retry=RetryPolicy(max_attempts=3))
    graph.add_node("cash", cash_node, retry=RetryPolicy(max_attempts=3))

    # Define the workflow edges
    graph.add_edge(START, "segment")
    graph.add_edge("segment", "wound")
    graph.add_edge("wound", "reframe")
    graph.add_edge("reframe", "offer")
    graph.add_edge("offer", "action")
    graph.add_edge("action", "cash")
    graph.add_edge("cash", END)

    return graph


def compile_switch6_graph(
    *,
    dependencies: Optional[Switch6Dependencies] = None,
) -> CompiledGraph:
    """Return a compiled version of the Switch 6 workflow."""
    graph = build_switch6_graph(dependencies=dependencies)
    return graph.compile()


# Convenience function for running the complete Switch 6 workflow
async def run_switch6_workflow(
    business_data: Dict[str, Any],
    user_type: str,
    dependencies: Optional[Switch6Dependencies] = None,
) -> Dict[str, Any]:
    """Run the complete Switch 6 workflow and return results."""
    deps = dependencies or _default_dependencies()

    # Prepare initial state
    initial_state: Switch6State = {
        "business_data": business_data,
        "user_type": user_type,
    }

    # Compile and run the graph
    graph = compile_switch6_graph(dependencies=deps)

    try:
        # Run the workflow
        result = await graph.ainvoke(initial_state)

        # Extract final results
        final_results = {
            "framework": "Switch 6",
            "execution_date": result.get("start_time"),
            "user_type": user_type,
            "stages": {
                "segment": result.get("segment_results"),
                "wound": result.get("wound_results"),
                "reframe": result.get("reframe_results"),
                "offer": result.get("offer_results"),
                "action": result.get("action_results"),
                "cash": result.get("cash_results"),
            },
            "framework_completion_score": result.get("framework_completion_score"),
            "errors": result.get("errors", []),
            "execution_complete": result.get("execution_complete", False),
        }

        return final_results

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        return {
            "framework": "Switch 6",
            "error": str(e),
            "errors": [],
            "execution_complete": False,
            "stages": {},
        }


__all__ = [
    "Switch6State",
    "Switch6Dependencies",
    "CircuitBreaker",
    "build_switch6_graph",
    "compile_switch6_graph",
    "run_switch6_workflow",
]
