"""
Web Crawler Agent - Scrapes web content and extracts structured data
"""
from utils.base_agent import BaseAgent
from .tools import scrape_url

class WebCrawlerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)

    async def execute(self, input_data):
        urls = input_data.get("urls", [])
        results = []
        for url in urls:
            result = await scrape_url(url)
            results.append({"url": url, "data": result})
        return {"results": results}

    def get_dependencies(self):
        return []
