"""Webhook agent enabling secure send/receive operations."""
from typing import Any, Dict, Mapping, Optional

from utils.base_agent import BaseAgent
from .tools import receive_webhook, send_webhook


class WebhookAgent(BaseAgent):
    """Coordinate webhook deliveries and signature validation."""

    async def execute(self, input_data: Mapping[str, Any]) -> Dict[str, Any]:
        if not isinstance(input_data, Mapping):
            return {"error": "input_data must be a mapping"}

        action = input_data.get("action", "send").lower()

        if action == "send":
            return await self._handle_send(input_data)
        if action == "receive":
            return await self._handle_receive(input_data)

        return {"error": f"Unknown webhook action '{action}'"}

    async def _handle_send(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        config = self.config
        return await send_webhook(
            url=payload.get("url"),
            payload=payload.get("payload", {}),
            headers=payload.get("headers"),
            timeout=payload.get("timeout", config.get("default_timeout", 10)),
            verify_ssl=payload.get("verify_ssl", config.get("verify_ssl", True)),
            secret=payload.get("secret") or config.get("signing_secret"),
            signature_header=payload.get("signature_header", config.get("signature_header", "X-Signature")),
            signature_method=payload.get("signature_method", config.get("signature_method", "sha256")),
            max_retries=payload.get("max_retries", config.get("max_retries", 3)),
            backoff_factor=payload.get("backoff_factor", config.get("backoff_factor", 0.5)),
            content_type=payload.get("content_type", config.get("default_content_type", "json")),
        )

    async def _handle_receive(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        config = self.config
        raw_body = payload.get("raw_body")
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")
        elif raw_body is None:
            raw_body = b""

        return await receive_webhook(
            raw_body=raw_body,
            headers=payload.get("headers", {}),
            secret=payload.get("secret") or config.get("signing_secret"),
            signature_header=payload.get("signature_header", config.get("signature_header", "X-Signature")),
            signature_method=payload.get("signature_method", config.get("signature_method", "sha256")),
            tolerance_seconds=payload.get("tolerance_seconds", config.get("tolerance_seconds")),
            timestamp_header=payload.get("timestamp_header", config.get("timestamp_header")),
        )

    def get_dependencies(self):
        return []
