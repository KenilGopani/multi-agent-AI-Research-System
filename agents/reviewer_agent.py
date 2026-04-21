from prompts.reviewer_prompts import REVIEWER_PROMPT
from state import ResearchState, ReviewResult
from utils.helpers import ainvoke_llm, parse_json_object, source_digest


def _default_review(error: str) -> ReviewResult:
    return ReviewResult(
        verdict="NEEDS_REVISION",
        score=5,
        issues=[f"Review could not be parsed or completed: {error}"],
        suggestions=["Improve source coverage, citation specificity, and report structure."],
    )


async def reviewer_agent(state: ResearchState) -> dict:
    print("Reviewer agent: checking report quality")
    prompt = REVIEWER_PROMPT.format(
        query=state["query"],
        sources=source_digest(state.get("scraped_content", [])),
        report=state.get("draft_report", ""),
    )

    try:
        response = await ainvoke_llm(prompt, label="report review")
        payload = parse_json_object(response)
        review = ReviewResult.model_validate(payload)
        print(f"Reviewer agent: verdict={review.verdict}, score={review.score}")
        return {"review_result": review, "errors": [], "status": "reviewed"}
    except Exception as exc:
        review = _default_review(str(exc))
        return {
            "review_result": review,
            "errors": [f"Reviewer failed: {exc}"],
            "status": "review_failed",
        }
