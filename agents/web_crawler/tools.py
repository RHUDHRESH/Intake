"""
Tools for Web Crawler Agent
"""
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_url(url):
    """Scrape content from a URL using Playwright and BeautifulSoup"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        html_content = await page.content()
        await browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string if soup.title else ""
    text = soup.get_text(separator="\n", strip=True)
    return {"title": title, "text": text}
