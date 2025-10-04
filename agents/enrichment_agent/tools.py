"""Utility helpers for the EnrichmentAgent."""
import asyncio
import json
import os
from copy import deepcopy
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Union

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

# Environment configuration references
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_GEOCODE_URL = os.getenv(
    "GOOGLE_GEOCODE_URL",
    "https://maps.googleapis.com/maps/api/geocode/json",
)

SocialLookupCallable = Callable[[Mapping[str, Any]], Awaitable[Mapping[str, Any]]]
MLCallable = Callable[[Mapping[str, Any], str], Awaitable[Mapping[str, Any]]]
CustomCallable = Union[
    Callable[[Dict[str, Any]], Dict[str, Any]],
    Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
]


def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, Mapping):
        return [dict(data)]
    return [dict(item) for item in data]


def _record_result(
    item: Dict[str, Any],
    enrichment_key: str,
    value: Any,
    meta: Dict[str, Any],
    error: Optional[str] = None,
) -> Dict[str, Any]:
    enriched_item = deepcopy(item)
    enriched_item[enrichment_key] = value
    if error:
        enriched_item.setdefault("enrichment_errors", []).append(error)
        meta["errors"].append({"item": item, "error": error})
    else:
        meta["enriched_count"] += 1
    return enriched_item


def _build_meta() -> Dict[str, Any]:
    return {"enriched_count": 0, "errors": []}


async def enrich_with_geo(
    data: Any,
    address_field: str,
    *,
    api_key: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
    rate_limit_ms: Optional[int] = None,
    cache: Optional[MutableMapping[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    api_key = api_key or GOOGLE_MAPS_API_KEY
    items = _normalize_items(data)
    meta = _build_meta()

    if not api_key:
        for item in items:
            error = "Missing GOOGLE_MAPS_API_KEY for geo enrichment"
            meta["errors"].append({"item": item, "error": error})
        return {"data": items, "meta": meta}

    cache = cache or {}
    created_session = False
    if session is None:
        created_session = True
        session = aiohttp.ClientSession(timeout=ClientTimeout(total=timeout))

    try:
        enriched_items: List[Dict[str, Any]] = []
        for item in items:
            address = item.get(address_field)
            if not address:
                enriched_items.append(_record_result(item, "geo", None, meta, "address missing"))
                continue

            cached = cache.get(address)
            if cached is not None:
                enriched_items.append(_record_result(item, "geo", cached, meta))
                continue

            params = {"address": address, "key": api_key}
            try:
                async with session.get(GOOGLE_GEOCODE_URL, params=params) as resp:
                    payload = await resp.json()
                    if payload.get("status") == "OK":
                        location = payload["results"][0]["geometry"]["location"]
                        cache[address] = location
                        enriched_items.append(_record_result(item, "geo", location, meta))
                    else:
                        error = payload.get("status", "unknown error")
                        enriched_items.append(_record_result(item, "geo", None, meta, error))
            except (ClientError, asyncio.TimeoutError, ClientResponseError) as exc:
                enriched_items.append(_record_result(item, "geo", None, meta, str(exc)))

            if rate_limit_ms:
                await asyncio.sleep(rate_limit_ms / 1000)

        return {"data": enriched_items, "meta": meta}
    finally:
        if created_session and session:
            await session.close()


async def enrich_with_social(
    data: Any,
    handle_field: str,
    *,
    lookup: Optional[SocialLookupCallable] = None,
) -> Dict[str, Any]:
    items = _normalize_items(data)
    meta = _build_meta()

    async def default_lookup(record: Mapping[str, Any]) -> Mapping[str, Any]:
        handle = record.get(handle_field)
        if not handle:
            return {}
        # Mocked payload; in production replace with API call
        return {
            "handle": handle,
            "followers": 0,
            "verified": False,
        }

    lookup = lookup or default_lookup

    enriched_items: List[Dict[str, Any]] = []
    for item in items:
        try:
            enriched_payload = await lookup(item)
            enriched_items.append(_record_result(item, "social", dict(enriched_payload), meta))
        except Exception as exc:  # pragma: no cover - protective wrapper
            enriched_items.append(_record_result(item, "social", None, meta, str(exc)))
    return {"data": enriched_items, "meta": meta}


async def enrich_with_ml(
    data: Any,
    model: str,
    *,
    inference_fn: Optional[MLCallable] = None,
) -> Dict[str, Any]:
    items = _normalize_items(data)
    meta = _build_meta()

    async def default_inference(record: Mapping[str, Any], model_name: str) -> Mapping[str, Any]:
        text = record.get("text", "")
        label = "positive" if "good" in text.lower() else "neutral"
        return {"model": model_name, "label": label}

    inference_fn = inference_fn or default_inference
    enriched_items: List[Dict[str, Any]] = []

    for item in items:
        try:
            result = await inference_fn(item, model)
            enriched_items.append(_record_result(item, "ml", dict(result), meta))
        except Exception as exc:
            enriched_items.append(_record_result(item, "ml", None, meta, str(exc)))

    return {"data": enriched_items, "meta": meta}


async def enrich_custom(
    data: Any,
    enrich_func: CustomCallable,
) -> Dict[str, Any]:
    if enrich_func is None:
        return {"error": "enrich_func is required"}

    items = _normalize_items(data)
    meta = _build_meta()
    enriched_items: List[Dict[str, Any]] = []

    for item in items:
        try:
            maybe_result = enrich_func(deepcopy(item))
            if asyncio.iscoroutine(maybe_result):
                maybe_result = await maybe_result
            if not isinstance(maybe_result, Mapping):
                raise TypeError("Custom enrichment must return a mapping")
            enriched_items.append(_record_result(item, "custom", dict(maybe_result), meta))
        except Exception as exc:  # pragma: no cover - user supplied code safety
            enriched_items.append(_record_result(item, "custom", None, meta, str(exc)))

    return {"data": enriched_items, "meta": meta}
