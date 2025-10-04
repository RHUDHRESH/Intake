"""
Social Media Intelligence Agent
"""
from typing import Any, Dict, List

from utils.base_agent import BaseAgent
from .tools import fetch_google_trends, fetch_reddit_posts


class SocialAgent(BaseAgent):
    """Fetches social media and trend data for supplied keywords."""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        keywords: List[str] = input_data.get("keywords", [])
        if not keywords:
            return {"reddit_results": [], "trends_results": []}

        reddit_limit = int(input_data.get("reddit_limit", self.config.get("reddit_limit", 5)))
        timeframe = input_data.get(
            "google_trends_timeframe", self.config.get("google_trends_timeframe", "now 7-d")
        )

        reddit_results: List[Dict[str, Any]] = []
        trends_results: List[Dict[str, Any]] = []

        for keyword in keywords:
            reddit_data = await fetch_reddit_posts(keyword, limit=reddit_limit)
            reddit_results.append({"keyword": keyword, "reddit": reddit_data})

            trends_data = await fetch_google_trends(keyword, timeframe=timeframe)
            trends_results.append({"keyword": keyword, "trends": trends_data})

        return {"reddit_results": reddit_results, "trends_results": trends_results}

    def get_dependencies(self) -> List[str]:
        return []
