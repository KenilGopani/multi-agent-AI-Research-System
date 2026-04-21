import config
from state import ResearchState
from tools.scraper_tool import scrape_urls


async def scraper_agent(state: ResearchState) -> dict:
    print("Scraper agent: extracting source content")
    targets = [(item.url, item.title) for item in state.get("search_results", [])[: config.MAX_URLS]]
    if not targets:
        return {
            "scraped_content": [],
            "errors": ["No search results were available to scrape"],
            "status": "scrape_failed",
        }

    scraped_content = await scrape_urls(targets)
    failed = [item for item in scraped_content if not item.success]
    errors = [f"Scrape failed for {item.url}: {item.error}" for item in failed]
    print(f"Scraper agent: {len(scraped_content) - len(failed)}/{len(scraped_content)} pages extracted")
    return {"scraped_content": scraped_content, "errors": errors, "status": "scraped"}
