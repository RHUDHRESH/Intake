"""
Notification channel helpers.
"""
import asyncio
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TIMEOUT = ClientTimeout(total=15)


def _build_email(recipient: str, message: str) -> EmailMessage:
    email = EmailMessage()
    email.set_content(message)
    email["Subject"] = "Notification"
    email["From"] = EMAIL_SENDER
    email["To"] = recipient
    return email


def _send_email_sync(recipient: str, message: str) -> Dict[str, Any]:
    if not all([EMAIL_SENDER, EMAIL_PASSWORD]):
        raise RuntimeError("Email configuration missing")
    email = _build_email(recipient, message)
    with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(email)
    return {"status": "sent", "platform": "email", "to": recipient}


def _send_sms_sync(recipient: str, message: str) -> Dict[str, Any]:
    # Placeholder until the Twilio SDK is wired in.
    print(f"SMS to {recipient}: {message}")
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
        return {
            "status": "mocked",
            "platform": "sms",
            "to": recipient,
            "note": "Configure Twilio credentials for real delivery",
        }
    return {
        "status": "queued",
        "platform": "sms",
        "to": recipient,
        "note": "Integrate Twilio client to send messages",
    }


async def _http_post(url: str, *, json_payload: Optional[Dict[str, Any]] = None, data=None):
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(url, json=json_payload, data=data) as resp:
            body = await resp.text()
            return resp.status, body


async def send_telegram(message: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    token = TELEGRAM_BOT_TOKEN
    target = chat_id or TELEGRAM_CHAT_ID
    if not token or not target:
        return {"error": "Telegram configuration missing"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": target, "text": message}
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, data=payload) as resp:
                resp_json = await resp.json()
                if resp.status != 200:
                    return {"error": resp_json, "platform": "telegram"}
                return {"status": "sent", "platform": "telegram", "details": resp_json}
    except (ClientError, asyncio.TimeoutError) as exc:
        return {"error": str(exc), "platform": "telegram"}


async def send_slack(message: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
    url = webhook_url or SLACK_WEBHOOK_URL
    if not url:
        return {"error": "Slack webhook URL missing"}
    payload = {"text": message}
    try:
        status, body = await _http_post(url, json_payload=payload)
        if status >= 400:
            return {"error": body, "platform": "slack"}
        return {"status": "sent", "platform": "slack"}
    except (ClientError, asyncio.TimeoutError) as exc:
        return {"error": str(exc), "platform": "slack"}


async def send_discord(message: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url:
        return {"error": "Discord webhook URL missing"}
    payload = {"content": message}
    try:
        status, body = await _http_post(url, json_payload=payload)
        if status >= 400:
            return {"error": body, "platform": "discord"}
        return {"status": "sent", "platform": "discord"}
    except (ClientError, asyncio.TimeoutError) as exc:
        return {"error": str(exc), "platform": "discord"}


async def send_email(message: str, recipient: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_send_email_sync, recipient, message)
    except (RuntimeError, smtplib.SMTPException) as exc:
        return {"error": str(exc), "platform": "email"}


async def send_sms(message: str, recipient: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_send_sms_sync, recipient, message)
    except RuntimeError as exc:
        return {"error": str(exc), "platform": "sms"}
