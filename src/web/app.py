"""FastAPI application factory for AnotherEdenAI web layer.

Lifespan handler initializes the Neo4j AsyncGraphDatabase driver singleton
(same pattern as src/workflow/run.py) and stores it in app.state.driver.
Also initializes app.state.jobs as an in-memory dict for the SSE job queue
(two-phase POST->GET pattern, single-worker uvicorn only).
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from neo4j import AsyncGraphDatabase

from .routes import pages, api, admin

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down app-level resources.

    Startup: create Neo4j driver singleton + empty job queue dict.
    Shutdown: close driver cleanly.
    """
    app.state.driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    app.state.jobs: dict = {}
    yield
    await app.state.driver.close()


app = FastAPI(
    title="AnotherEdenAI",
    description="GraphRAG team builder for Another Eden",
    lifespan=lifespan,
)

# Mount static files (app.js, etc.)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(admin.router)
