"""
Utility functions for the NLPAgent.
"""
import asyncio
import json
import os
import re
from typing import List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

SUMMARY_MODEL = os.getenv("HF_SUMMARY_MODEL", "facebook/bart-large-cnn")
SENTIMENT_MODEL = os.getenv(
    "HF_SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
)
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "hf_demo_token")
API_BASE_URL = "https://api-inference.huggingface.co/models"
CLIENT_HEADERS = (
    {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    if HUGGINGFACE_API_TOKEN
    else {}
)
TIMEOUT = ClientTimeout(total=45)


async def summarize_text(text: str) -> Optional[str]:
    """Return a summary for the provided text."""
    if not text.strip():
        return None

    url = f"{API_BASE_URL}/{SUMMARY_MODEL}"
    payload = {"inputs": text}

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, headers=CLIENT_HEADERS, json=payload) as resp:
                if resp.status != 200:
                    return None
                resp_json = await resp.json()
    except (ClientError, asyncio.TimeoutError, json.JSONDecodeError):
        return None

    if isinstance(resp_json, list) and resp_json:
        return resp_json[0].get("summary_text")
    if isinstance(resp_json, dict):
        return resp_json.get("summary_text")
    return None


async def tag_text(text: str, limit: int = 8) -> List[str]:
    """Generate simple keyword-style tags from text."""
    if not text:
        return []

    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    seen = set()
    tags: List[str] = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        tags.append(word)
        if len(tags) >= limit:
            break
    return tags


async def sentiment_analysis(text: str) -> Optional[str]:
    """Return the sentiment label for provided text."""
    if not text.strip():
        return None

    url = f"{API_BASE_URL}/{SENTIMENT_MODEL}"
    payload = {"inputs": text}

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, headers=CLIENT_HEADERS, json=payload) as resp:
                if resp.status != 200:
                    return None
                resp_json = await resp.json()
    except (ClientError, asyncio.TimeoutError, json.JSONDecodeError):
        return None

    if isinstance(resp_json, list) and resp_json:
        entry = resp_json[0]
        label = entry.get("label")
        score = entry.get("score")
        if label is not None and score is not None:
            return f"{label} ({score:.2f})"
        return label
    if isinstance(resp_json, dict):
        return resp_json.get("label")
    return None
