"""API routes — entities, query, and SSE stream endpoints."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.sse import EventSourceResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from ..dependencies import get_driver
from ..streaming import pipeline_sse_generator

router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class QueryRequest(BaseModel):
    query: str
    roster: list[str]
    owned_sidekicks: list[str] = Field(default_factory=list)


@router.get("/entities")
async def get_entities(driver=Depends(get_driver)):
    """Return Character and Sidekick names for ownership checklists.

    Build items come from graph-backed recommendation context, not player ownership.
    Returns: {"characters": [str, ...], "sidekicks": [str, ...]}
    """
    records, _, _ = await driver.execute_query(
        "MATCH (c:Character) RETURN c.name AS name, 'Character' AS type "
        "UNION ALL "
        "MATCH (s:Sidekick) RETURN s.name AS name, 'Sidekick' AS type "
        "ORDER BY name",
        database_="neo4j",
    )
    sidekicks = [r["name"] for r in records if r["type"] == "Sidekick"]
    sidekick_names = {name.casefold() for name in sidekicks}
    characters = [
        r["name"]
        for r in records
        if r["type"] == "Character" and r["name"].casefold() not in sidekick_names
    ]
    return {"characters": characters, "sidekicks": sidekicks}


@router.post("/query")
async def post_query(body: QueryRequest, request: Request):
    """Accept query + roster, enqueue the job, return HTMX SSE progress fragment.

    Two-phase POST->SSE-GET pattern (per D-09 architectural fix):
    1. This POST stores the job payload in app.state.jobs[job_id]
    2. Returns an HTML fragment whose sse-connect URL includes the job_id
    3. HTMX swaps the fragment, automatically opening the SSE GET connection
    """
    job_id = str(uuid4())
    request.app.state.jobs[job_id] = {
        "query": body.query,
        "roster": body.roster,
        "owned_sidekicks": body.owned_sidekicks,
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={"job_id": job_id},
    )


@router.get("/stream/{job_id}", response_class=EventSourceResponse)
async def stream_job(job_id: str, request: Request, driver=Depends(get_driver)):
    """SSE stream for a pending pipeline job.

    Looks up job_id in app.state.jobs, runs the LangGraph pipeline via
    pipeline_sse_generator(), streams events to the HTMX client.

    Returns 404 if job_id is not found (e.g., already consumed or invalid UUID).
    Deletes the job from app.state.jobs before streaming (single-use job store).
    """
    jobs = request.app.state.jobs
    job_data = jobs.pop(job_id, None)
    if job_data is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    # ServerSentEvent must be yielded directly from the path operation so
    # FastAPI's routing layer handles SSE wire encoding. Wrapping in
    # EventSourceResponse(generator) tries to .encode() the dataclass as bytes
    # and crashes silently after sending 200 OK headers.
    async for event in pipeline_sse_generator(
        query=job_data["query"],
        roster=job_data["roster"],
        driver=driver,
        templates=templates,
        request=request,
        owned_sidekicks=job_data.get("owned_sidekicks", []),
    ):
        yield event
