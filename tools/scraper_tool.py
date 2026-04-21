import asyncio
from typing import Optional

import httpx
import requests
from bs4 import BeautifulSoup

import config
from state import ScrapedContent
from utils.helpers import clean_text, trim_to_tokens

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_main_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        element.decompose()

    title = clean_text(soup.title.get_text(" ")) if soup.title else "Untitled"
    selectors = [
        "article",
        "main",
        "[role='main']",
        ".article",
        ".post-content",
        ".entry-content",
        ".content",
    ]

    candidates = []
    for selector in selectors:
        candidates.extend(soup.select(selector))

    if candidates:
        best = max(candidates, key=lambda node: len(node.get_text(" ", strip=True)))
        text = best.get_text("\n", strip=True)
    else:
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n\n".join(p for p in paragraphs if len(p) > 30)

    return title, clean_text(text)


async def _fetch_with_httpx(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=config.SCRAPE_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def scrape_url(url: str, title_hint: Optional[str] = None) -> ScrapedContent:
    try:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=config.SCRAPE_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()
            html = response.text
        except Exception as requests_error:
            print(f"  ! requests failed for {url}: {requests_error}. Trying httpx")
            html = await _fetch_with_httpx(url)

        title, text = extract_main_text(html)
        text = trim_to_tokens(text, config.MAX_CONTENT_LEN)
        if len(text) < 200:
            return ScrapedContent(
                url=url,
                title=title_hint or title,
                content=text,
                success=False,
                error="Extracted content was under 200 characters",
            )

        return ScrapedContent(url=url, title=title_hint or title, content=text, success=True)
    except Exception as exc:
        return ScrapedContent(url=url, title=title_hint or url, content="", success=False, error=str(exc))


async def scrape_urls(items: list[tuple[str, str]]) -> list[ScrapedContent]:
    scraped: list[ScrapedContent] = []
    for index, (url, title) in enumerate(items, start=1):
        print(f"  → Scraping {index}/{len(items)}: {url}")
        scraped.append(await scrape_url(url, title))
        if index < len(items):
            await asyncio.sleep(config.SCRAPER_DELAY_SECONDS)
    return scraped
