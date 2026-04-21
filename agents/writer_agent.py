from prompts.writer_prompts import WRITER_PROMPT
from state import ResearchState
from utils.helpers import ainvoke_llm, source_digest


def _revision_notes(state: ResearchState) -> str:
    review = state.get("review_result")
    if state.get("revision_count", 0) <= 0 or review is None:
        return ""
    suggestions = "\n".join(f"- {item}" for item in review.suggestions)
    issues = "\n".join(f"- {item}" for item in review.issues)
    return f"Revision notes:\nIssues:\n{issues}\n\nRequired fixes:\n{suggestions}"


async def writer_agent(state: ResearchState) -> dict:
    current_revision_count = state.get("revision_count", 0)
    next_revision_count = current_revision_count + 1 if state.get("draft_report") else current_revision_count
    print(f"Writer agent: drafting report (revision {next_revision_count})")

    sources = source_digest(state.get("scraped_content", []))
    if not sources:
        sources = "No source content was successfully scraped. Write a brief failure report explaining missing evidence."

    prompt = WRITER_PROMPT.format(
        query=state["query"],
        sources=sources,
        revision_notes=_revision_notes(state),
    )

    try:
        draft_report = await ainvoke_llm(prompt, label="report writing")
        return {
            "draft_report": draft_report,
            "revision_count": next_revision_count,
            "errors": [],
            "status": "drafted",
        }
    except Exception as exc:
        fallback = (
            f"# Research Report: {state['query']}\n\n"
            "The report could not be generated because all configured LLM providers failed.\n\n"
            f"Error: {exc}\n"
        )
        return {
            "draft_report": fallback,
            "revision_count": next_revision_count,
            "errors": [f"Writer failed: {exc}"],
            "status": "write_failed",
        }
