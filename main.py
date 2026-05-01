import asyncio
import os
import re
import sys

import config
from graph.research_graph import build_graph
from state import ResearchState


async def run_research(query: str, max_revisions: int = config.MAX_REVISIONS):
    initial_state: ResearchState = {
        "query": query,
        "search_results": [],
        "scraped_content": [],
        "draft_report": "",
        "review_result": None,
        "final_report": "",
        "revision_count": 0,
        "max_revisions": max_revisions,
        "status": "running",
        "errors": [],
    }

    print(f"\nStarting research for: {query}\n")
    graph = build_graph()
    final_state = dict(initial_state)

    async for event in graph.astream(initial_state):
        for node_name, state_update in event.items():
            if isinstance(state_update, dict):
                if "errors" in state_update:
                    final_state["errors"] = final_state.get("errors", []) + state_update.pop("errors")
                final_state.update(state_update)
                status = state_update.get("status")
            else:
                status = None
            suffix = f" ({status})" if status else ""
            print(f"  ✓ {node_name} agent completed{suffix}")

    if final_state.get("errors"):
        print("\nWarnings:")
        for error in final_state["errors"]:
            print(f"- {error}")

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(final_state["final_report"])

    # Save report to a file
    filename = re.sub(r'[^\w\s-]', '', query.lower())
    filename = re.sub(r'[-\s]+', '_', filename).strip('_')
    if not filename:
        filename = "research_report"
    filename = f"{filename}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(final_state["final_report"])
        
    print(f"\n[+] Report successfully saved to: {filename}")

    return final_state["final_report"]


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "Impact of AI on healthcare in 2025"
    asyncio.run(run_research(query))
