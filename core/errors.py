"""Shared error taxonomy for the agent platform."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type


@dataclass
class AgentError(Exception):
    """Base class for structured agent exceptions."""

    message: str
    code: str = "agent_error"
    retryable: bool = False
    http_status: int = 500
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "http_status": self.http_status,
            "details": self.details,
        }


class ConfigurationError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="configuration_error",
            retryable=False,
            http_status=500,
            details=details,
        )


class ValidationError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="validation_error",
            retryable=False,
            http_status=400,
            details=details,
        )


class AuthenticationError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="authentication_error",
            retryable=False,
            http_status=401,
            details=details,
        )


class AuthorizationError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="authorization_error",
            retryable=False,
            http_status=403,
            details=details,
        )


class RateLimitError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="rate_limited",
            retryable=True,
            http_status=429,
            details=details,
        )


class ExternalServiceError(AgentError):
    def __init__(self, message: str, *, retryable: bool = True, **details: Any) -> None:
        super().__init__(
            message=message,
            code="external_service_error",
            retryable=retryable,
            http_status=503 if retryable else 500,
            details=details,
        )


class HumanInputRequiredError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="hitl_required",
            retryable=False,
            http_status=428,
            details=details,
        )


class RetryableAgentError(AgentError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(
            message=message,
            code="retryable_error",
            retryable=True,
            http_status=503,
            details=details,
        )


ERROR_CODE_MAP: Dict[str, Type[AgentError]] = {
    "agent_error": AgentError,
    "configuration_error": ConfigurationError,
    "validation_error": ValidationError,
    "authentication_error": AuthenticationError,
    "authorization_error": AuthorizationError,
    "rate_limited": RateLimitError,
    "external_service_error": ExternalServiceError,
    "hitl_required": HumanInputRequiredError,
    "retryable_error": RetryableAgentError,
}


def coerce_agent_error(error: Exception) -> AgentError:
    """Return *error* as an :class:`AgentError`."""

    if isinstance(error, AgentError):
        return error
    return AgentError(message=str(error))
