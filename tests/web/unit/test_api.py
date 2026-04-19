"""Unit tests for GET /api/entities and POST /api/query — WEB-02."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetEntities:
    def test_get_entities_returns_characters_and_grastas(self, test_client, stub_driver):
        """GET /api/entities returns JSON with characters and grastas keys."""
        # Override stub to return mixed Character + Grasta records
        stub_driver.execute_query = AsyncMock(
            return_value=(
                [
                    {"name": "Aldo", "type": "Character"},
                    {"name": "Ciel", "type": "Character"},
                    {"name": "All-Round Grasta", "type": "Grasta"},
                ],
                None,
                None,
            )
        )
        response = test_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert "grastas" in data
        assert "Aldo" in data["characters"]
        assert "All-Round Grasta" in data["grastas"]

    def test_get_entities_empty_db(self, test_client, stub_driver):
        """GET /api/entities returns empty lists when Neo4j returns no records."""
        stub_driver.execute_query = AsyncMock(return_value=([], None, None))
        response = test_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert data["characters"] == []
        assert data["grastas"] == []


class TestPostQuery:
    def test_post_query_returns_sse_fragment(self, test_client):
        """POST /api/query returns HTML fragment containing sse-connect URL (WEB-02, two-phase pattern)."""
        response = test_client.post(
            "/api/query",
            json={"query": "best blunt team", "roster": ["Aldo", "Ciel"]},
        )
        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "/api/stream/" in response.text

    def test_post_query_stores_job_in_state(self, test_client):
        """POST /api/query stores job payload in app.state.jobs keyed by UUID."""
        from src.web.app import app as web_app
        response = test_client.post(
            "/api/query",
            json={"query": "best team", "roster": ["Aldo"]},
        )
        assert response.status_code == 200
        # The job should be stored (at least one entry)
        assert len(web_app.state.jobs) >= 1
