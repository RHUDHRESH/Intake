"""Human-in-the-loop Review Agent."""
from typing import Any, Dict, Tuple

from utils.base_agent import AgentInput, BaseAgent
from .tools import record_review_action, send_review_request


class ReviewAgent(BaseAgent):
    """Coordinates reviews by notifying human reviewers."""

    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        input_data = agent_input.input_data
        content = input_data.get("content")
        workflow_id = input_data.get("workflow_id")
        reviewer = input_data.get("reviewer")

        if not all([content, workflow_id, reviewer]):
            return {"error": "content, workflow_id, and reviewer are required"}

        channel = input_data.get("channel") or self.config.get("review_method", "telegram")
        review_link = await send_review_request(content, workflow_id, reviewer, channel=channel)
        await record_review_action(workflow_id, reviewer, "sent")
        return {"review_link": review_link, "channel": channel}

    def get_dependencies(self) -> Tuple[str, ...]:
        return tuple()
