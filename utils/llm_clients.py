"""Client helpers for GPT-5 Nano and related LLM operations with feature flag support."""
from __future__ import annotations

import json
import os
import random
import re
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

# Import feature flag system
try:
    from .feature_flags import (
        get_feature_manager,
        get_ai_model_config,
        is_gpt5_nano_enabled,
        is_openai_fallback_enabled,
        are_custom_endpoints_enabled,
        is_model_analytics_enabled,
        ModelProvider
    )
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class LLMChoice:
    text: str


@dataclass
class LLMResponse:
    choices: List[LLMChoice]


class EnhancedLLMClient:
    """Enhanced LLM client with feature flag support and intelligent fallback."""

    def __init__(
        self,
        *,
        model: str = "gpt-5-nano",
        use_feature_flags: bool = True,
        enable_analytics: bool = True,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.use_feature_flags = use_feature_flags and FEATURE_FLAGS_AVAILABLE
        self.enable_analytics = enable_analytics and (self.use_feature_flags and is_model_analytics_enabled())
        self.max_retries = max_retries

        # Initialize feature flag manager if available
        self.feature_manager = get_feature_manager() if self.use_feature_flags else None
        self.ai_config = get_ai_model_config() if self.use_feature_flags else None

        # Performance tracking
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0

        # Build provider clients
        self._provider_clients = self._build_provider_clients()

    def _build_provider_clients(self) -> Dict[str, Any]:
        """Build clients for available providers."""
        clients = {}

        if not self.use_feature_flags:
            # Legacy mode - use original logic
            if OpenAI and os.getenv("OPENAI_API_KEY"):
                try:
                    clients["openai"] = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {e}")
            return clients

        # Feature flag mode - use configured endpoints
        if not self.ai_config:
            logger.warning("No AI configuration available, using legacy mode")
            return clients

        # Build clients for active endpoints
        for endpoint_name, endpoint in self.ai_config.endpoints.items():
            if endpoint.is_available():
                if endpoint.provider == ModelProvider.OPENAI and OpenAI:
                    try:
                        api_key = os.getenv(endpoint.api_key_env_var)
                        if api_key:
                            clients[endpoint_name] = OpenAI(api_key=api_key)
                    except Exception as e:
                        logger.warning(f"Failed to initialize {endpoint_name} client: {e}")

        return clients

    def generate(self, prompt: str, *, temperature: float = 0.7, max_tokens: int = 256) -> LLMResponse:
        """Generate response with intelligent fallback and analytics."""
        start_time = time.time()
        self._request_count += 1

        # Determine generation strategy
        if self.use_feature_flags and self.ai_config:
            return self._generate_with_feature_flags(prompt, temperature, max_tokens, start_time)
        else:
            return self._generate_legacy(prompt, temperature, max_tokens, start_time)

    def _generate_with_feature_flags(self, prompt: str, temperature: float, max_tokens: int, start_time: float) -> LLMResponse:
        """Generate using feature flag configuration."""
        if not self.ai_config:
            return self._generate_legacy(prompt, temperature, max_tokens, start_time)

        # Try each endpoint in priority order
        for endpoint_name in self.ai_config.fallback_chain:
            endpoint = self.ai_config.endpoints.get(endpoint_name)
            if not endpoint or not endpoint.is_available():
                continue

            response = self._try_endpoint(endpoint, prompt, temperature, max_tokens)
            if response:
                latency = time.time() - start_time
                self._total_latency += latency
                if self.enable_analytics:
                    self._record_analytics(endpoint_name, "success", latency)
                return response

        # All endpoints failed, use fallback
        latency = time.time() - start_time
        self._error_count += 1
        if self.enable_analytics:
            self._record_analytics("fallback", "error", latency)

        return LLMResponse(choices=[LLMChoice(text=self._enhanced_fallback(prompt))])

    def _generate_legacy(self, prompt: str, temperature: float, max_tokens: int, start_time: float) -> LLMResponse:
        """Legacy generation method for backward compatibility."""
        # Try GPT-5 Nano endpoint if available
        endpoint = os.getenv("GPT5_NANO_ENDPOINT")
        api_key = os.getenv("GPT5_NANO_API_KEY")

        if endpoint and requests and api_key:
            if self._try_gpt5_nano_endpoint(endpoint, api_key, prompt, temperature, max_tokens):
                latency = time.time() - start_time
                self._total_latency += latency
                if self.enable_analytics:
                    self._record_analytics("gpt5_nano", "success", latency)
                return LLMResponse(choices=[LLMChoice(text="Success via GPT-5 Nano")])

        # Try OpenAI
        if "openai" in self._provider_clients:
            try:
                completion = self._provider_clients["openai"].chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a marketing strategist."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                texts = [
                    choice.message.content.strip()
                    for choice in completion.choices
                    if getattr(choice, "message", None) and choice.message.content
                ]
                if texts:
                    latency = time.time() - start_time
                    self._total_latency += latency
                    if self.enable_analytics:
                        self._record_analytics("openai", "success", latency)
                    return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}")

        # All methods failed
        latency = time.time() - start_time
        self._error_count += 1
        if self.enable_analytics:
            self._record_analytics("legacy_fallback", "error", latency)

        return LLMResponse(choices=[LLMChoice(text=self._enhanced_fallback(prompt))])

    def _try_endpoint(self, endpoint, prompt: str, temperature: float, max_tokens: int) -> Optional[LLMResponse]:
        """Try to generate using a specific endpoint."""
        try:
            if endpoint.provider == ModelProvider.OPENAI:
                return self._try_openai_endpoint(endpoint, prompt, temperature, max_tokens)
            elif endpoint.provider == ModelProvider.GPT5_NANO:
                return self._try_gpt5_nano_endpoint_configured(endpoint, prompt, temperature, max_tokens)
            elif endpoint.provider == ModelProvider.CUSTOM:
                return self._try_custom_endpoint(endpoint, prompt, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Endpoint {endpoint.provider.value} failed: {e}")

        return None

    def _try_openai_endpoint(self, endpoint, prompt: str, temperature: float, max_tokens: int) -> Optional[LLMResponse]:
        """Try OpenAI-compatible endpoint."""
        client_name = None
        for name, client in self._provider_clients.items():
            if name == "openai":  # Find OpenAI client
                client_name = name
                break

        if not client_name:
            return None

        try:
            completion = self._provider_clients[client_name].chat.completions.create(
                model=endpoint.model_name,
                messages=[
                    {"role": "system", "content": "You are a marketing strategist."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            texts = [
                choice.message.content.strip()
                for choice in completion.choices
                if getattr(choice, "message", None) and choice.message.content
            ]
            if texts:
                return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
        except Exception as e:
            logger.warning(f"OpenAI endpoint failed: {e}")

        return None

    def _try_gpt5_nano_endpoint_configured(self, endpoint, prompt: str, temperature: float, max_tokens: int) -> Optional[LLMResponse]:
        """Try GPT-5 Nano endpoint using feature flag configuration."""
        api_key = os.getenv(endpoint.api_key_env_var)
        if not api_key or not requests:
            return None

        payload = {
            "model": endpoint.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        for attempt in range(endpoint.max_retries):
            try:
                response = requests.post(
                    endpoint.endpoint_url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=endpoint.timeout
                )
                response.raise_for_status()
                body = response.json()
                texts = self._extract_texts(body)
                if texts:
                    return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
            except Exception as e:
                if attempt == endpoint.max_retries - 1:
                    logger.warning(f"GPT-5 Nano endpoint failed after {endpoint.max_retries} attempts: {e}")
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff

        return None

    def _try_custom_endpoint(self, endpoint, prompt: str, temperature: float, max_tokens: int) -> Optional[LLMResponse]:
        """Try custom endpoint."""
        api_key = os.getenv(endpoint.api_key_env_var)
        if not api_key or not requests:
            return None

        payload = {
            "model": endpoint.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            response = requests.post(
                endpoint.endpoint_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=endpoint.timeout
            )
            response.raise_for_status()
            body = response.json()
            texts = self._extract_texts(body)
            if texts:
                return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
        except Exception as e:
            logger.warning(f"Custom endpoint failed: {e}")

        return None

    def _try_gpt5_nano_endpoint(self, endpoint: str, api_key: str, prompt: str, temperature: float, max_tokens: int) -> bool:
        """Legacy GPT-5 Nano endpoint attempt (returns bool for backward compatibility)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _extract_texts(self, payload: Dict[str, Any]) -> List[str]:
        if "choices" in payload and isinstance(payload["choices"], list):
            texts: List[str] = []
            for choice in payload["choices"]:
                text = choice.get("text") or choice.get("message", {}).get("content")
                if isinstance(text, str):
                    texts.append(text.strip())
            return texts
        if "output" in payload and isinstance(payload["output"], str):
            return [payload["output"].strip()]
        return []

    def _enhanced_fallback(self, prompt: str) -> str:
        """Enhanced fallback with better keyword extraction."""
        keywords = re.findall(r"[A-Za-z0-9]+", prompt)
        seed = sum(ord(c) for c in prompt) % 9973
        random.seed(seed)

        # Marketing-focused fallback responses
        hooks = [
            "remarkable",
            "irresistible",
            "share-worthy",
            "tribe-ready",
            "behavioral nudge",
            "purple cow",
            "permission-based",
            "authentic approach",
            "positioning strategy",
            "attention-grabbing"
        ]

        hook = random.choice(hooks)
        summary = " ".join(keywords[:12])

        # Create more marketing-focused response
        return f"{hook.title()}: {summary[:160]} — Apply strategic marketing principles for maximum impact."

    def _record_analytics(self, endpoint_name: str, status: str, latency: float):
        """Record analytics for model performance."""
        if not self.feature_manager:
            return

        # This would typically send to analytics service
        logger.info(f"Model Analytics - Endpoint: {endpoint_name}, Status: {status}, Latency: {latency:.2f}s")


class LLMClient:
    """Legacy wrapper that resolves GPT-5 Nano endpoint with offline fallbacks."""

    def __init__(
        self,
        *,
        model: str = "gpt-5-nano",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> None:
        self.model = model
        self.endpoint = endpoint or os.getenv("GPT5_NANO_ENDPOINT")
        self.api_key = api_key or os.getenv("GPT5_NANO_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.organization = organization or os.getenv("OPENAI_ORG")
        self._openai_client = self._build_openai_client()

    def _build_openai_client(self) -> Optional[Any]:
        if OpenAI is None or not self.api_key:
            return None
        try:
            return OpenAI(api_key=self.api_key, organization=self.organization)
        except Exception:  # pragma: no cover - credentials/runtime
            return None

    def generate(self, prompt: str, *, temperature: float = 0.7, max_tokens: int = 256) -> LLMResponse:
        if self.endpoint and requests is not None and self.api_key:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            try:
                response = requests.post(self.endpoint, headers=headers, data=json.dumps(payload), timeout=30)
                response.raise_for_status()
                body = response.json()
                texts = self._extract_texts(body)
                if texts:
                    return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
            except Exception:  # pragma: no cover - endpoint failure
                pass

        if self._openai_client is not None:
            try:
                completion = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a marketing strategist."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                texts = [
                    choice.message.content.strip()
                    for choice in completion.choices
                    if getattr(choice, "message", None) and choice.message.content
                ]
                if texts:
                    return LLMResponse(choices=[LLMChoice(text=t) for t in texts])
            except Exception:  # pragma: no cover - API failure
                pass

        return LLMResponse(choices=[LLMChoice(text=self._fallback(prompt))])

    def _extract_texts(self, payload: Dict[str, Any]) -> List[str]:
        if "choices" in payload and isinstance(payload["choices"], list):
            texts: List[str] = []
            for choice in payload["choices"]:
                text = choice.get("text") or choice.get("message", {}).get("content")
                if isinstance(text, str):
                    texts.append(text.strip())
            return texts
        if "output" in payload and isinstance(payload["output"], str):
            return [payload["output"].strip()]
        return []

    def _fallback(self, prompt: str) -> str:
        keywords = re.findall(r"[A-Za-z0-9]+", prompt)
        seed = sum(ord(c) for c in prompt) % 9973
        random.seed(seed)
        hook = random.choice([
            "remarkable",
            "irresistible",
            "share-worthy",
            "tribe-ready",
            "behavioral nudge",
        ])
        summary = " ".join(keywords[:12])
        return f"{hook.title()}: {summary[:160]}"


_default_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def get_enhanced_llm() -> EnhancedLLMClient:
    """Get enhanced LLM client with feature flag support."""
    return EnhancedLLMClient()


# Global enhanced client
_enhanced_client: Optional[EnhancedLLMClient] = None


def get_enhanced_llm_client() -> EnhancedLLMClient:
    """Get the global enhanced LLM client instance."""
    global _enhanced_client
    if _enhanced_client is None:
        _enhanced_client = EnhancedLLMClient()
    return _enhanced_client


__all__ = [
    "LLMClient",
    "EnhancedLLMClient",
    "LLMChoice",
    "LLMResponse",
    "get_llm",
    "get_enhanced_llm",
    "get_enhanced_llm_client"
]
