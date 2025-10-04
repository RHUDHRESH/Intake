"""
Notification Agent for multi-channel alerts.
"""
from typing import Any, Dict

from utils.base_agent import BaseAgent
from .tools import send_discord, send_email, send_slack, send_sms, send_telegram


class NotificationAgent(BaseAgent):
    """Dispatches messages to supported notification channels."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        method = input_data.get("method", self.config.get("default_method", "telegram"))
        message = input_data.get("message", "")
        recipient = input_data.get("to")

        if not method:
            return {"error": "Notification method is required"}
        if not message:
            return {"error": "Message content is required"}

        normalized = method.lower()
        if normalized == "telegram":
            return await send_telegram(message, recipient)
        if normalized == "slack":
            return await send_slack(message, recipient)
        if normalized == "discord":
            return await send_discord(message, recipient)
        if normalized == "email":
            if not recipient:
                return {"error": "Email recipient is required"}
            return await send_email(message, recipient)
        if normalized == "sms":
            if not recipient:
                return {"error": "SMS recipient is required"}
            return await send_sms(message, recipient)

        return {"error": f"Unsupported notification method: {method}"}

    def get_dependencies(self):
        return []
