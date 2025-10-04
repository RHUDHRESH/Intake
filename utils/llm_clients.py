"""Client helpers for GPT-5 Nano and related LLM operations."""
from __future__ import annotations

import json
import os
import random
import re
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


@dataclass
class LLMChoice:
    text: str


@dataclass
class LLMResponse:
    choices: List[LLMChoice]


class LLMClient:
    """Wrapper that resolves GPT-5 Nano endpoint with offline fallbacks."""

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


__all__ = ["LLMClient", "LLMChoice", "LLMResponse", "get_llm"]
