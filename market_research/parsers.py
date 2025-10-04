from __future__ import annotations

from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

from .interfaces import HTMLParser


class SoupHTMLParser(HTMLParser):
    """Extracts headings, meta tags, and body text from HTML."""

    def __init__(self, *, text_limit: int = 8000) -> None:
        self._text_limit = text_limit

    def parse(self, html: str, *, url: Optional[str] = None) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()
        h_tags = [node.get_text(strip=True) for node in soup.find_all(["h1", "h2", "h3"])]
        text = soup.get_text(separator="\n", strip=True)
        if len(text) > self._text_limit:
            text = text[: self._text_limit]
        return {
            "url": url,
            "title": title,
            "description": description,
            "headings": h_tags,
            "text": text,
        }


__all__ = ["SoupHTMLParser"]
