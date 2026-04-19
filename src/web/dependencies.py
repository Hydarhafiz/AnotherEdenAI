"""FastAPI dependency providers for the web layer."""
import os
import secrets

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from neo4j import AsyncDriver

admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def get_driver(request: Request) -> AsyncDriver:
    """Return the app-level Neo4j driver singleton from app.state."""
    return request.app.state.driver


def verify_admin_key(api_key: str | None = Security(admin_key_header)) -> str:
    """Validate X-Admin-Key header against ADMIN_KEY env var.

    Raises HTTPException(403) if key is missing or does not match.
    Uses secrets.compare_digest() for timing-safe comparison (ASVS V4).
    """
    expected = os.getenv("ADMIN_KEY", "")
    if not expected or not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header")
    return api_key
