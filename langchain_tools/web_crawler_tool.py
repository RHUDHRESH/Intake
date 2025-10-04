"""LangChain tool for crawling web pages via Playwright."""
import asyncio
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, HttpUrl, validator
from playwright.async_api import async_playwright


class WebCrawlerInput(BaseModel):
    url: HttpUrl = Field(..., description="Fully qualified URL to crawl")
    wait_for_selector: Optional[str] = Field(
        None,
        description="Optional CSS selector to await before extracting page contents",
    )
    timeout_ms: int = Field(
        30000,
        description="Navigation timeout (milliseconds) when loading the page",
        ge=1000,
        le=120000,
    )
    text_limit: int = Field(
        5000,
        description="Maximum number of text characters to return from the page body",
        ge=500,
        le=50000,
    )

    @validator("url", pre=True)
    def strip_url(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class WebCrawlerTool(BaseTool):
    name = "web_crawler_tool"
    description = (
        "Fetches a web page using Playwright, returning the title, raw HTML, and "
        "a text extract suitable for downstream summarisation or embedding."
    )
    args_schema: type = WebCrawlerInput

    def _run(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        timeout_ms: int = 30000,
        text_limit: int = 5000,
    ) -> Dict[str, Any]:
        return asyncio.run(
            self._arun(
                url=url,
                wait_for_selector=wait_for_selector,
                timeout_ms=timeout_ms,
                text_limit=text_limit,
            )
        )

    async def _arun(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        timeout_ms: int = 30000,
        text_limit: int = 5000,
    ) -> Dict[str, Any]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
            html = await page.content()
            status = response.status if response else None
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n", strip=True)
        if len(text) > text_limit:
            text = text[:text_limit]

        return {
            "url": url,
            "status": status,
            "title": title,
            "text": text,
            "html": html,
        }
