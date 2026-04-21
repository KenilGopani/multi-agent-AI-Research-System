from prompts.research_prompts import SEARCH_QUERY_PROMPT
from state import ResearchState, SearchResult
from tools.search_tool import tavily_search
from utils.helpers import ainvoke_llm, normalize_url


def _fallback_queries(query: str) -> list[str]:
    return [
        query,
        f"{query} latest research credible sources",
        f"{query} analysis report 2025",
    ]


def _parse_queries(text: str, original_query: str) -> list[str]:
    queries = []
    for line in text.splitlines():
        cleaned = line.strip(" -0123456789.\t")
        if cleaned:
            queries.append(cleaned)
    if not queries:
        queries = _fallback_queries(original_query)
    return queries[:3]


async def research_agent(state: ResearchState) -> dict:
    query = state["query"]
    errors: list[str] = []
    print("Research agent: generating optimized search queries")

    try:
        prompt = SEARCH_QUERY_PROMPT.format(query=query)
        query_text = await ainvoke_llm(prompt, label="search query generation")
        search_queries = _parse_queries(query_text, query)
    except Exception as exc:
        errors.append(f"Search query generation failed: {exc}")
        search_queries = _fallback_queries(query)

    print(f"Research agent: searching {len(search_queries)} query variants")
    ranked: dict[str, SearchResult] = {}
    for search_query in search_queries:
        try:
            results = await tavily_search(search_query, max_results=8)
            for result in results:
                key = normalize_url(result.url)
                if not key:
                    continue
                existing = ranked.get(key)
                if existing is None or result.score > existing.score:
                    ranked[key] = result
        except Exception as exc:
            errors.append(f"Search failed for '{search_query}': {exc}")

    search_results = sorted(ranked.values(), key=lambda item: item.score, reverse=True)[:8]
    print(f"Research agent: selected {len(search_results)} unique sources")
    return {"search_results": search_results, "errors": errors, "status": "searched"}
