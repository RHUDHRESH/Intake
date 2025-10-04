"""
Feature flag system for managing AI model endpoints and API connections.

This module provides a centralized configuration system for:
- GPT-5 Nano endpoints and API connections
- Multiple AI model providers and fallbacks
- Environment-based feature toggling
- Dynamic configuration updates
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported AI model providers."""
    GPT5_NANO = "gpt5_nano"
    OPENAI = "openai"
    CUSTOM = "custom"
    MOCK = "mock"


class FeatureStatus(Enum):
    """Feature flag status."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    BETA = "beta"
    DEPRECATED = "deprecated"


@dataclass
class ModelEndpoint:
    """Configuration for a specific model endpoint."""
    provider: ModelProvider
    endpoint_url: str
    api_key_env_var: str
    model_name: str
    enabled: bool = True
    priority: int = 100
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 256
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if this endpoint is available (has API key and is enabled)."""
        return self.enabled and bool(os.getenv(self.api_key_env_var))


@dataclass
class FeatureFlag:
    """Individual feature flag configuration."""
    name: str
    status: FeatureStatus
    enabled: bool
    description: str
    config: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if this feature flag is currently active."""
        return self.enabled and self.status in [FeatureStatus.ENABLED, FeatureStatus.BETA]


@dataclass
class AIModelConfig:
    """Configuration for AI model connections."""
    default_provider: ModelProvider
    endpoints: Dict[str, ModelEndpoint]
    fallback_chain: List[str]
    global_settings: Dict[str, Any] = field(default_factory=dict)

    def get_active_endpoints(self) -> List[ModelEndpoint]:
        """Get all currently active endpoints sorted by priority."""
        active = [ep for ep in self.endpoints.values() if ep.is_available()]
        return sorted(active, key=lambda x: x.priority)

    def get_best_endpoint(self) -> Optional[ModelEndpoint]:
        """Get the highest priority available endpoint."""
        active = self.get_active_endpoints()
        return active[0] if active else None


class FeatureFlagManager:
    """Centralized feature flag and configuration manager."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("FEATURE_FLAGS_CONFIG", "feature_flags.json")
        self._config: Dict[str, Any] = {}
        self._feature_flags: Dict[str, FeatureFlag] = {}
        self._ai_config: Optional[AIModelConfig] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from file and environment."""
        # Load from file if it exists
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                self._config = {}

        # Override with environment variables
        self._load_environment_overrides()

        # Initialize feature flags
        self._initialize_feature_flags()

        # Initialize AI model configuration
        self._initialize_ai_config()

    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables."""
        # AI Model endpoints
        if os.getenv("GPT5_NANO_ENDPOINT"):
            self._config.setdefault("ai_models", {}).setdefault("endpoints", {})["gpt5_nano"] = {
                "provider": "gpt5_nano",
                "endpoint_url": os.getenv("GPT5_NANO_ENDPOINT"),
                "api_key_env_var": "GPT5_NANO_API_KEY",
                "model_name": "gpt-5-nano",
                "enabled": os.getenv("GPT5_NANO_ENABLED", "true").lower() == "true",
                "priority": int(os.getenv("GPT5_NANO_PRIORITY", "100")),
                "timeout": int(os.getenv("GPT5_NANO_TIMEOUT", "30"))
            }

        # Feature flag overrides
        for key, value in os.environ.items():
            if key.startswith("FEATURE_") and key.endswith("_ENABLED"):
                flag_name = key[8:-7].lower()  # Remove FEATURE_ prefix and _ENABLED suffix
                self._config.setdefault("features", {})[flag_name] = {
                    "enabled": value.lower() == "true",
                    "status": os.getenv(f"FEATURE_{flag_name.upper()}_STATUS", "enabled")
                }

    def _initialize_feature_flags(self):
        """Initialize feature flags from configuration."""
        default_features = {
            "gpt5_nano": {
                "name": "gpt5_nano",
                "status": "enabled",
                "enabled": True,
                "description": "Enable GPT-5 Nano model endpoints"
            },
            "openai_fallback": {
                "name": "openai_fallback",
                "status": "enabled",
                "enabled": True,
                "description": "Enable OpenAI as fallback when GPT-5 Nano unavailable"
            },
            "custom_endpoints": {
                "name": "custom_endpoints",
                "status": "beta",
                "enabled": False,
                "description": "Enable custom model endpoints"
            },
            "model_analytics": {
                "name": "model_analytics",
                "status": "enabled",
                "enabled": True,
                "description": "Enable analytics and performance tracking for model calls"
            },
            "dynamic_fallback": {
                "name": "dynamic_fallback",
                "status": "enabled",
                "enabled": True,
                "description": "Enable dynamic fallback to simpler models when complex ones fail"
            }
        }

        features_config = self._config.get("features", {})

        for flag_name, default_config in default_features.items():
            flag_config = features_config.get(flag_name, {})
            merged_config = {**default_config, **flag_config}

            try:
                status = FeatureStatus(merged_config.get("status", "enabled"))
            except ValueError:
                status = FeatureStatus.ENABLED

            self._feature_flags[flag_name] = FeatureFlag(
                name=merged_config["name"],
                status=status,
                enabled=merged_config["enabled"],
                description=merged_config["description"],
                config=merged_config.get("config", {})
            )

    def _initialize_ai_config(self):
        """Initialize AI model configuration."""
        ai_config = self._config.get("ai_models", {})

        # Default endpoints configuration
        default_endpoints = {
            "gpt5_nano": ModelEndpoint(
                provider=ModelProvider.GPT5_NANO,
                endpoint_url=ai_config.get("gpt5_nano_endpoint", ""),
                api_key_env_var="GPT5_NANO_API_KEY",
                model_name="gpt-5-nano",
                enabled=self.is_enabled("gpt5_nano"),
                priority=100,
                timeout=30
            ),
            "openai": ModelEndpoint(
                provider=ModelProvider.OPENAI,
                endpoint_url="https://api.openai.com/v1/chat/completions",
                api_key_env_var="OPENAI_API_KEY",
                model_name="gpt-4",
                enabled=self.is_enabled("openai_fallback"),
                priority=200,
                timeout=30
            ),
            "mock": ModelEndpoint(
                provider=ModelProvider.MOCK,
                endpoint_url="mock://localhost",
                api_key_env_var="",
                model_name="mock",
                enabled=True,
                priority=1000,
                timeout=1
            )
        }

        # Merge with configured endpoints
        endpoints_config = ai_config.get("endpoints", {})
        endpoints = {}

        for endpoint_name, default_endpoint in default_endpoints.items():
            endpoint_config = endpoints_config.get(endpoint_name, {})
            if endpoint_config:
                # Update existing endpoint with config
                endpoints[endpoint_name] = ModelEndpoint(
                    provider=ModelProvider(endpoint_config.get("provider", default_endpoint.provider.value)),
                    endpoint_url=endpoint_config.get("endpoint_url", default_endpoint.endpoint_url),
                    api_key_env_var=endpoint_config.get("api_key_env_var", default_endpoint.api_key_env_var),
                    model_name=endpoint_config.get("model_name", default_endpoint.model_name),
                    enabled=endpoint_config.get("enabled", default_endpoint.enabled),
                    priority=endpoint_config.get("priority", default_endpoint.priority),
                    timeout=endpoint_config.get("timeout", default_endpoint.timeout),
                    max_retries=endpoint_config.get("max_retries", default_endpoint.max_retries),
                    temperature=endpoint_config.get("temperature", default_endpoint.temperature),
                    max_tokens=endpoint_config.get("max_tokens", default_endpoint.max_tokens),
                    metadata=endpoint_config.get("metadata", {})
                )
            else:
                endpoints[endpoint_name] = default_endpoint

        # Default fallback chain
        fallback_chain = ai_config.get("fallback_chain", ["gpt5_nano", "openai", "mock"])

        self._ai_config = AIModelConfig(
            default_provider=ModelProvider(ai_config.get("default_provider", "gpt5_nano")),
            endpoints=endpoints,
            fallback_chain=fallback_chain,
            global_settings=ai_config.get("global_settings", {})
        )

    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        feature = self._feature_flags.get(feature_name)
        return feature.is_active() if feature else False

    def get_feature_flag(self, feature_name: str) -> Optional[FeatureFlag]:
        """Get a specific feature flag."""
        return self._feature_flags.get(feature_name)

    def get_all_feature_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags."""
        return self._feature_flags.copy()

    def get_ai_config(self) -> Optional[AIModelConfig]:
        """Get AI model configuration."""
        return self._ai_config

    def enable_feature(self, feature_name: str) -> bool:
        """Enable a feature flag."""
        if feature_name in self._feature_flags:
            self._feature_flags[feature_name].enabled = True
            self._save_config()
            return True
        return False

    def disable_feature(self, feature_name: str) -> bool:
        """Disable a feature flag."""
        if feature_name in self._feature_flags:
            self._feature_flags[feature_name].enabled = False
            self._save_config()
            return True
        return False

    def set_feature_status(self, feature_name: str, status: FeatureStatus) -> bool:
        """Set the status of a feature flag."""
        if feature_name in self._feature_flags:
            self._feature_flags[feature_name].status = status
            self._save_config()
            return True
        return False

    def add_custom_endpoint(self, name: str, endpoint: ModelEndpoint) -> bool:
        """Add a custom model endpoint."""
        if self._ai_config:
            self._ai_config.endpoints[name] = endpoint
            self._save_config()
            return True
        return False

    def remove_endpoint(self, name: str) -> bool:
        """Remove a model endpoint."""
        if self._ai_config and name in self._ai_config.endpoints:
            del self._ai_config.endpoints[name]
            self._save_config()
            return True
        return False

    def update_endpoint_priority(self, name: str, priority: int) -> bool:
        """Update the priority of a model endpoint."""
        if self._ai_config and name in self._ai_config.endpoints:
            self._ai_config.endpoints[name].priority = priority
            self._save_config()
            return True
        return False

    def _save_config(self):
        """Save current configuration to file."""
        try:
            # Convert dataclasses to dictionaries for JSON serialization
            config_to_save = {
                "features": {
                    name: {
                        "name": flag.name,
                        "status": flag.status.value,
                        "enabled": flag.enabled,
                        "description": flag.description,
                        "config": flag.config
                    }
                    for name, flag in self._feature_flags.items()
                },
                "ai_models": {
                    "default_provider": self._ai_config.default_provider.value if self._ai_config else "gpt5_nano",
                    "endpoints": {
                        name: {
                            "provider": endpoint.provider.value,
                            "endpoint_url": endpoint.endpoint_url,
                            "api_key_env_var": endpoint.api_key_env_var,
                            "model_name": endpoint.model_name,
                            "enabled": endpoint.enabled,
                            "priority": endpoint.priority,
                            "timeout": endpoint.timeout,
                            "max_retries": endpoint.max_retries,
                            "temperature": endpoint.temperature,
                            "max_tokens": endpoint.max_tokens,
                            "metadata": endpoint.metadata
                        }
                        for name, endpoint in self._ai_config.endpoints.items() if self._ai_config
                    },
                    "fallback_chain": self._ai_config.fallback_chain if self._ai_config else ["gpt5_nano", "openai", "mock"],
                    "global_settings": self._ai_config.global_settings if self._ai_config else {}
                }
            }

            with open(self.config_path, 'w') as f:
                json.dump(config_to_save, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def reload_config(self):
        """Reload configuration from file and environment."""
        self._config = {}
        self._feature_flags = {}
        self._ai_config = None
        self._load_config()


# Global instance
_feature_manager: Optional[FeatureFlagManager] = None


def get_feature_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance."""
    global _feature_manager
    if _feature_manager is None:
        _feature_manager = FeatureFlagManager()
    return _feature_manager


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    return get_feature_manager().is_enabled(feature_name)


def get_ai_model_config() -> Optional[AIModelConfig]:
    """Get the current AI model configuration."""
    return get_feature_manager().get_ai_config()


# Convenience functions for common checks
def is_gpt5_nano_enabled() -> bool:
    """Check if GPT-5 Nano is enabled."""
    return is_feature_enabled("gpt5_nano")


def is_openai_fallback_enabled() -> bool:
    """Check if OpenAI fallback is enabled."""
    return is_feature_enabled("openai_fallback")


def are_custom_endpoints_enabled() -> bool:
    """Check if custom endpoints are enabled."""
    return is_feature_enabled("custom_endpoints")


def is_model_analytics_enabled() -> bool:
    """Check if model analytics is enabled."""
    return is_feature_enabled("model_analytics")


__all__ = [
    "FeatureFlagManager",
    "ModelProvider",
    "FeatureStatus",
    "ModelEndpoint",
    "FeatureFlag",
    "AIModelConfig",
    "get_feature_manager",
    "is_feature_enabled",
    "get_ai_model_config",
    "is_gpt5_nano_enabled",
    "is_openai_fallback_enabled",
    "are_custom_endpoints_enabled",
    "is_model_analytics_enabled"
]
