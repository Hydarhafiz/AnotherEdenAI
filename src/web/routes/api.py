"""API routes — entities, query, and SSE stream endpoints."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..dependencies import get_driver

router = APIRouter(prefix="/api")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


class QueryRequest(BaseModel):
    query: str
    roster: list[str]


@router.get("/entities")
async def get_entities(driver=Depends(get_driver)):
    """Return all Character and Grasta names for the roster checklist.

    Uses UNION ALL so both node types are returned in one round-trip.
    Returns: {"characters": [str, ...], "grastas": [str, ...]}
    """
    records, _, _ = await driver.execute_query(
        "MATCH (c:Character) RETURN c.name AS name, 'Character' AS type "
        "UNION ALL "
        "MATCH (g:Grasta) RETURN g.name AS name, 'Grasta' AS type "
        "ORDER BY name",
        database_="neo4j",
    )
    characters = [r["name"] for r in records if r["type"] == "Character"]
    grastas = [r["name"] for r in records if r["type"] == "Grasta"]
    return {"characters": characters, "grastas": grastas}


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
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/progress.html",
        context={"job_id": job_id},
    )
