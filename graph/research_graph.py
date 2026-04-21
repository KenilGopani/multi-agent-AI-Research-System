from langgraph.graph import END, StateGraph

from agents import research_agent, reviewer_agent, scraper_agent, writer_agent
from state import ResearchState


def route_after_review(state: ResearchState) -> str:
    review = state.get("review_result")
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if revision_count >= max_revisions:
        return "approved"

    if review and review.verdict == "APPROVED":
        return "approved"

    return "needs_revision"


def finalize_report(state: ResearchState) -> dict:
    return {
        "final_report": state["draft_report"],
        "status": "complete",
    }


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("research", research_agent)
    graph.add_node("scrape", scraper_agent)
    graph.add_node("write", writer_agent)
    graph.add_node("review", reviewer_agent)
    graph.add_node("finalize", finalize_report)

    graph.set_entry_point("research")
    graph.add_edge("research", "scrape")
    graph.add_edge("scrape", "write")
    graph.add_edge("write", "review")
    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "approved": "finalize",
            "needs_revision": "write",
        },
    )
    graph.add_edge("finalize", END)

    return graph.compile()
