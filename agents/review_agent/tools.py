"""
Utility helpers for ReviewAgent.
"""
import asyncio
import os
from typing import Any, Dict

import aiohttp
from aiohttp import ClientError, ClientTimeout

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEOUT = ClientTimeout(total=15)


async def send_review_request(
    content: str,
    workflow_id: str,
    reviewer: str,
    channel: str = "telegram",
) -> str:
    """Trigger a review notification to the configured channel."""
    if channel == "telegram" and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        message = f"Review needed for workflow {workflow_id} by {reviewer}:\n{content}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload: Dict[str, Any] = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        try:
            async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
                async with session.post(url, data=payload) as resp:
                    if resp.status != 200:
                        return f"telegram-error-{workflow_id}"
                    resp_json = await resp.json()
        except (ClientError, asyncio.TimeoutError):
            return f"telegram-error-{workflow_id}"
        message_id = resp_json.get("result", {}).get("message_id")
        return f"telegram://message/{message_id}" if message_id else f"telegram-sent-{workflow_id}"

    # Fallback: console logging/mock link
    print(f"[HITL Review] Reviewer: {reviewer}\nWorkflow: {workflow_id}\nContent: {content}")
    return f"mock-review-link-{workflow_id}"


async def record_review_action(workflow_id: str, reviewer: str, action: str) -> bool:
    """Record the review action. Currently prints to stdout."""
    print(f"Review {action} for workflow {workflow_id} by {reviewer}")
    return True
