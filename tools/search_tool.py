from urllib.parse import urlparse

from tavily import TavilyClient

import config
from state import SearchResult
from utils.helpers import normalize_url, with_retries


def is_high_quality_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if not parsed.scheme.startswith("http") or not host:
        return False
    return not any(host == domain or host.endswith(f".{domain}") for domain in config.LOW_QUALITY_DOMAINS)


async def tavily_search(query: str, max_results: int = 8) -> list[SearchResult]:
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set")

    async def run_search() -> list[SearchResult]:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )
        results = []
        for item in response.get("results", []):
            url = normalize_url(item.get("url", ""))
            if not is_high_quality_url(url):
                continue
            results.append(
                SearchResult(
                    url=url,
                    title=item.get("title") or url,
                    snippet=item.get("content") or "",
                    score=float(item.get("score") or 0.0),
                )
            )
        return results

    return await with_retries(run_search, retries=config.SEARCH_RETRIES, label=f"Tavily search: {query}")
