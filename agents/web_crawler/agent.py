"""Web Crawler Agent - Scrapes web content and extracts structured data."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from utils.base_agent import AgentInput, BaseAgent
from .tools import scrape_url


class WebCrawlerAgent(BaseAgent):
    """Fetches web pages and performs lightweight content analysis."""

    _URL_PATTERN = re.compile(r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE)
    _EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    _PHONE_PATTERN = re.compile(r"\b\+?\d[\d\s().-]{7,}\d\b")
    _POSITIVE_WORDS = {"good", "great", "excellent", "amazing", "best", "positive", "success", "happy"}
    _NEGATIVE_WORDS = {"bad", "poor", "terrible", "awful", "worst", "negative", "failure", "sad"}

    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        input_data = agent_input.input_data
        urls = list(input_data.get("urls", []))

        candidate_texts = [
            input_data.get("website"),
            input_data.get("text"),
            input_data.get("description"),
        ]
        for text in candidate_texts:
            if isinstance(text, str):
                urls.extend(self.extract_urls_from_text(text))

        urls = self._sanitize_urls(urls)

        max_pages = int(self.get_config_value("max_pages", len(urls) or 0))
        if max_pages > 0:
            urls = urls[:max_pages]

        if not urls:
            return {
                "message": "No URLs found in input payload.",
                "pages_crawled": 0,
                "results": [],
                "structured_data": {},
            }

        pages = []
        for url in urls:
            page = await self.fetch_page_content(url)
            pages.append(page)

        corpus_text = " ".join(page.get("text_content", "") for page in pages)
        structured_data = {
            "keywords": self.extract_keywords(corpus_text),
            "contact_info": self.extract_contact_info(corpus_text),
            "sentiment": self.analyze_sentiment(corpus_text),
        }

        return {
            "message": f"Crawled {len(pages)} page(s)",
            "pages_crawled": len(pages),
            "results": pages,
            "structured_data": structured_data,
            "summary": self._summarise_pages(pages),
        }

    def get_dependencies(self) -> Tuple[str, ...]:
        return tuple()

    async def fetch_page_content(self, url: str) -> Dict[str, Any]:
        raw = await scrape_url(url)
        text_content = raw.get("text", "") if isinstance(raw, dict) else ""
        return {
            "url": url,
            "title": raw.get("title", "") if isinstance(raw, dict) else "",
            "text_content": text_content,
            "links": self.extract_urls_from_text(text_content),
            "images": [],
            "headings": {"h1": [], "h2": [], "h3": []},
            "meta_description": raw.get("title", "") if isinstance(raw, dict) else "",
            "status_code": raw.get("status", 200) if isinstance(raw, dict) else 200,
        }

    def extract_urls_from_text(self, text: str) -> List[str]:
        return list({match.group(0) for match in self._URL_PATTERN.finditer(text or "")})

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        tokens = [token.lower() for token in re.findall(r"[A-Za-z]{3,}", text or "")]
        frequency = Counter(tokens)
        most_common = [word for word, _ in frequency.most_common(max_keywords)]
        return most_common

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        tokens = {token.lower() for token in re.findall(r"[A-Za-z]+", text or "")}
        positive_hits = len(tokens & self._POSITIVE_WORDS)
        negative_hits = len(tokens & self._NEGATIVE_WORDS)
        if positive_hits > negative_hits:
            sentiment = "positive"
        elif negative_hits > positive_hits:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        return {
            "sentiment": sentiment,
            "positive_terms": sorted(tokens & self._POSITIVE_WORDS),
            "negative_terms": sorted(tokens & self._NEGATIVE_WORDS),
        }

    def extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        emails = list({match.group(0) for match in self._EMAIL_PATTERN.finditer(text or "")})
        phones = list({match.group(0) for match in self._PHONE_PATTERN.finditer(text or "")})
        return {"emails": emails, "phones": phones}

    def is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:  # noqa: BLE001 - defensive parsing
            return False

    def _sanitize_urls(self, urls: Iterable[str]) -> List[str]:
        seen = set()
        cleaned = []
        for url in urls:
            if not isinstance(url, str):
                continue
            candidate = url.strip()
            if not candidate or not self.is_valid_url(candidate):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            cleaned.append(candidate)
        return cleaned

    def _summarise_pages(self, pages: Iterable[Dict[str, Any]]) -> str:
        lines = []
        for page in pages:
            title = page.get("title") or "(untitled)"
            lines.append(f"{page.get('url')}: {title}")
        return "\n".join(lines)
