"""
Natural Language Processing Agent
"""
from typing import Any, Dict

from utils.base_agent import BaseAgent
from .tools import sentiment_analysis, summarize_text, tag_text


class NLPAgent(BaseAgent):
    """Processes text to generate summaries, tags, and sentiment."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        text = input_data.get("text", "")
        if not text:
            return {}

        result: Dict[str, Any] = {}

        summary = await summarize_text(text)
        if summary is not None:
            result["summary"] = summary

        max_keywords = int(self.config.get("max_keywords", 8))
        tags = await tag_text(text, limit=max_keywords)
        if tags:
            result["tags"] = tags

        sentiment = await sentiment_analysis(text)
        if sentiment is not None:
            result["sentiment"] = sentiment

        return result

    def get_dependencies(self):
        return []
