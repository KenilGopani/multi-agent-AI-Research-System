"""
FastAPI backend for the Multi-Agent AI Research System.

Provides REST endpoints and Server-Sent Events (SSE) streaming
so the frontend can display agent progress in real-time.
"""

import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from graph.research_graph import build_graph
from state import ResearchState

# ─── In-memory store for research jobs ─────────────────────────────────────────

jobs: Dict[str, Dict[str, Any]] = {}


# ─── Pydantic request / response models ────────────────────────────────────────


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="The research topic to investigate")
    max_revisions: int = Field(default=config.MAX_REVISIONS, ge=0, le=5)


class JobResponse(BaseModel):
    job_id: str
    query: str
    status: str
    created_at: str


class JobStatusResponse(BaseModel):
    job_id: str
    query: str
    status: str
    created_at: str
    events: List[Dict[str, Any]]
    report: Optional[str] = None
    errors: List[str]


# ─── LLM Cache setup ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the LLM response cache on startup."""
    from langchain.globals import set_llm_cache
    from langchain_community.cache import SQLiteCache

    set_llm_cache(SQLiteCache(database_path=".langchain.db"))
    yield


# ─── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent AI Research System",
    description="Autonomous research pipeline powered by LangGraph, Groq & Gemini",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ────────────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_") or "research_report"


async def _run_pipeline(job_id: str, query: str, max_revisions: int):
    """Run the LangGraph pipeline and stream progress events into the job store."""
    job = jobs[job_id]

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

    graph = build_graph()
    final_state = dict(initial_state)

    try:
        async for event in graph.astream(initial_state):
            for node_name, state_update in event.items():
                if isinstance(state_update, dict):
                    if "errors" in state_update:
                        final_state["errors"] = final_state.get("errors", []) + state_update.pop("errors")
                    final_state.update(state_update)
                    status = state_update.get("status", "")
                else:
                    status = ""

                job["events"].append(
                    {
                        "agent": node_name,
                        "status": status,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        # Save the markdown report to disk
        filename = f"{_slugify(query)}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_state.get("final_report", ""))

        job["status"] = "completed"
        job["report"] = final_state.get("final_report", "")
        job["errors"] = final_state.get("errors", [])
        job["filename"] = filename

    except Exception as exc:
        job["status"] = "failed"
        job["errors"].append(str(exc))


# ─── Endpoints ──────────────────────────────────────────────────────────────────


@app.post("/api/research", response_model=JobResponse, status_code=202)
async def start_research(request: ResearchRequest):
    """Kick off a new research job. Returns immediately with a job ID."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    jobs[job_id] = {
        "job_id": job_id,
        "query": request.query,
        "status": "running",
        "created_at": now,
        "events": [],
        "report": None,
        "errors": [],
    }

    # Fire and forget – the pipeline runs in the background
    asyncio.create_task(_run_pipeline(job_id, request.query, request.max_revisions))

    return JobResponse(job_id=job_id, query=request.query, status="running", created_at=now)


@app.get("/api/research/{job_id}", response_model=JobStatusResponse)
async def get_research_status(job_id: str):
    """Poll the status of a research job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return JobStatusResponse(**job)


@app.get("/api/research/{job_id}/stream")
async def stream_research(job_id: str):
    """
    Server-Sent Events (SSE) endpoint.
    The frontend connects here and receives real-time agent progress updates.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_index = 0
        while True:
            job = jobs[job_id]
            events = job["events"]

            # Send any new events since last check
            while last_index < len(events):
                evt = events[last_index]
                import json

                yield f"data: {json.dumps(evt)}\n\n"
                last_index += 1

            # If the job finished, send final event and close
            if job["status"] in ("completed", "failed"):
                import json

                final = {
                    "agent": "system",
                    "status": job["status"],
                    "report": job.get("report"),
                    "errors": job.get("errors", []),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(final)}\n\n"
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs():
    """List all research jobs."""
    return [
        JobResponse(
            job_id=j["job_id"],
            query=j["query"],
            status=j["status"],
            created_at=j["created_at"],
        )
        for j in sorted(jobs.values(), key=lambda x: x["created_at"], reverse=True)
    ]


# ─── Serve frontend static files (must be last) ────────────────────────────────
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
