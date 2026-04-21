import operator
from typing import Annotated, List, Optional, TypedDict

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    score: float = 0.0


class ScrapedContent(BaseModel):
    url: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None


class ReviewResult(BaseModel):
    verdict: str = Field(pattern="^(APPROVED|NEEDS_REVISION)$")
    score: int = Field(ge=1, le=10)
    issues: List[str]
    suggestions: List[str]


class ResearchState(TypedDict):
    query: str
    search_results: List[SearchResult]
    scraped_content: List[ScrapedContent]
    draft_report: str
    review_result: Optional[ReviewResult]
    final_report: str
    revision_count: int
    max_revisions: int
    status: str
    errors: Annotated[List[str], operator.add]
