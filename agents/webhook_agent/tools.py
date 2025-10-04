"""Webhook utilities for sending and receiving signed HTTP callbacks."""
import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout


@dataclass
class WebhookSendResult:
    status: int
    response: Any
    headers: Mapping[str, Any]
    duration_ms: float
    attempts: int

@dataclass
class WebhookError:
    status: str
    error: str
    attempts: int
    duration_ms: float


DEFAULT_HEADERS = {"Content-Type": "application/json"}
SUPPORTED_CONTENT_TYPES = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "text": "text/plain",
}


class SignatureError(Exception):
    """Raised when webhook signatures cannot be verified."""


class WebhookTimeoutError(Exception):
    """Raised when webhook sending exceeds configured timeout."""


async def send_webhook(
    url: str,
    payload: Any,
    *,
    headers: Optional[Mapping[str, str]] = None,
    timeout: float = 10.0,
    verify_ssl: bool = True,
    secret: Optional[str] = None,
    signature_header: str = "X-Signature",
    signature_method: str = "sha256",
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    content_type: str = "json",
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, Any]:
    if not url:
        return {"status": "error", "error": "URL is required"}

    content_type = content_type.lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        return {"status": "error", "error": f"Unsupported content type '{content_type}'"}

    prepared_headers: Dict[str, str] = dict(DEFAULT_HEADERS)
    if headers:
        prepared_headers.update(headers)
    prepared_headers["Content-Type"] = SUPPORTED_CONTENT_TYPES[content_type]

    if content_type == "json":
        body_str = json.dumps(payload)
        body_bytes = body_str.encode("utf-8")
    elif content_type == "form" and isinstance(payload, Mapping):
        body_bytes = aiohttp.FormData(payload).encode()
    else:
        body_bytes = str(payload).encode("utf-8")

    if secret:
        signature = _sign_payload(body_bytes, secret, signature_method)
        prepared_headers[signature_header] = signature

    attempt = 0
    start_time = time.perf_counter()
    session_owner = False

    try:
        if session is None:
            session_owner = True
            session = aiohttp.ClientSession()
        timeout_ctx = ClientTimeout(total=timeout)

        while True:
            attempt += 1
            try:
                async with session.post(
                    url,
                    data=body_bytes,
                    headers=prepared_headers,
                    timeout=timeout_ctx,
                    ssl=verify_ssl,
                ) as resp:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    text = await resp.text()
                    response_body = _decode_response(text, resp.headers)
                    return WebhookSendResult(
                        status=resp.status,
                        response=response_body,
                        headers=dict(resp.headers),
                        duration_ms=duration_ms,
                        attempts=attempt,
                    ).__dict__
            except (ClientResponseError, ClientError, asyncio.TimeoutError) as exc:
                if attempt > max_retries:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return WebhookError(
                        status="error",
                        error=str(exc),
                        attempts=attempt,
                        duration_ms=duration_ms,
                    ).__dict__
                await asyncio.sleep(backoff_factor * (2 ** (attempt - 1)))
    finally:
        if session_owner and session:
            await session.close()


async def receive_webhook(
    raw_body: bytes,
    headers: Mapping[str, Any],
    *,
    secret: Optional[str] = None,
    signature_header: str = "X-Signature",
    signature_method: str = "sha256",
    tolerance_seconds: Optional[int] = None,
    timestamp_header: Optional[str] = None,
) -> Dict[str, Any]:
    if secret:
        try:
            _validate_signature(
                raw_body,
                headers,
                secret=secret,
                signature_header=signature_header,
                signature_method=signature_method,
                tolerance_seconds=tolerance_seconds,
                timestamp_header=timestamp_header,
            )
        except SignatureError as exc:
            return {"valid": False, "error": str(exc)}

    try:
        parsed = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        parsed = raw_body.decode("utf-8", errors="replace")

    return {"valid": True, "data": parsed}


def _sign_payload(body: bytes, secret: str, method: str) -> str:
    method = method.lower()
    if method not in {"sha256", "sha1", "md5"}:
        raise ValueError(f"Unsupported signature method '{method}'")
    digestmod = getattr(hashlib, method)
    signature = hmac.new(secret.encode("utf-8"), body, digestmod=digestmod).hexdigest()
    return signature


def _validate_signature(
    body: bytes,
    headers: Mapping[str, Any],
    *,
    secret: str,
    signature_header: str,
    signature_method: str,
    tolerance_seconds: Optional[int],
    timestamp_header: Optional[str],
) -> None:
    provided = headers.get(signature_header)
    if not provided:
        raise SignatureError("Signature header missing")

    if timestamp_header and tolerance_seconds:
        timestamp_val = headers.get(timestamp_header)
        if not timestamp_val:
            raise SignatureError("Timestamp header missing")
        try:
            timestamp = int(timestamp_val)
        except (ValueError, TypeError):
            raise SignatureError("Invalid timestamp header")
        now = int(time.time())
        if abs(now - timestamp) > tolerance_seconds:
            raise SignatureError("Signature timestamp outside tolerance window")
        payload = f"{timestamp}.{body.decode('utf-8', errors='replace')}".encode("utf-8")
    else:
        payload = body

    expected = _sign_payload(payload, secret, signature_method)
    if not hmac.compare_digest(provided, expected):
        raise SignatureError("Signature mismatch")


def _decode_response(text: str, headers: Mapping[str, Any]) -> Any:
    content_type = headers.get("Content-Type", "").split(";")[0].lower()
    if "json" in content_type:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text
