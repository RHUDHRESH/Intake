"""
Utility functions for the SocialAgent.
"""
import asyncio
import json
from typing import Any, Dict, List
from urllib.parse import quote_plus

import aiohttp
from aiohttp import ClientError, ClientTimeout

USER_AGENT = "intake-system-social-agent/0.1"


async def fetch_reddit_posts(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch top Reddit search results for a keyword."""
    if not keyword:
        return []

    encoded_keyword = quote_plus(keyword)
    url = f"https://www.reddit.com/search.json?q={encoded_keyword}&limit={limit}"
    headers = {"User-Agent": USER_AGENT}

    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=15)) as session:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except (ClientError, asyncio.TimeoutError, json.JSONDecodeError):
        return []

    children = data.get("data", {}).get("children", [])
    posts: List[Dict[str, Any]] = []
    for post in children:
        post_data = post.get("data", {})
        title = post_data.get("title", "")
        permalink = post_data.get("permalink", "")
        score = post_data.get("score")
        posts.append(
            {
                "title": title,
                "url": f"https://reddit.com{permalink}" if permalink else "",
                "score": score,
                "subreddit": post_data.get("subreddit"),
            }
        )
    return posts


async def fetch_google_trends(keyword: str, timeframe: str = "now 7-d") -> Dict[str, Any]:
    """Fetch Google Trends data for a keyword.

    This uses the public widget endpoint which may require a valid token. Replace the token
    with a fresh value or substitute with an official client for production usage.
    """
    if not keyword:
        return {}

    request_payload = {
        "time": timeframe,
        "resolution": "DAY",
        "locale": "en-US",
        "comparisonItem": [{"keyword": keyword, "geo": ""}],
        "requestOptions": {"property": "", "backend": "IZG", "category": 0},
    }
    encoded_req = quote_plus(json.dumps(request_payload, ensure_ascii=False))
    url = (
        "https://trends.google.com/trends/api/widgetdata/multiline?req="
        f"{encoded_req}&token=APP6_XXX&tz=0"
    )
    headers = {"User-Agent": USER_AGENT}

    try:
        async with aiohttp.ClientSession(timeout=ClientTimeout(total=15)) as session:
            async with session.get(url, headers=headers) as resp:
                resp.raise_for_status()
                raw_text = await resp.text()
    except (ClientError, asyncio.TimeoutError):
        return {}

    cleaned = raw_text.lstrip(")]}'\n ")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw": cleaned}
