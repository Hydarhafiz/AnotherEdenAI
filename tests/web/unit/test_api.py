"""Unit tests for GET /api/entities and POST /api/query — WEB-02."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetEntities:
    def test_get_entities_returns_characters_and_sidekicks(self, test_client, stub_driver):
        """GET /api/entities returns only ownership-selectable entity types."""
        # Override stub to return mixed Character and Sidekick records
        stub_driver.execute_query = AsyncMock(
            return_value=(
                [
                    {"name": "Aldo", "type": "Character"},
                    {"name": "Ciel", "type": "Character"},
                    {"name": "Tetra", "type": "Sidekick"},
                ],
                None,
                None,
            )
        )
        response = test_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert "sidekicks" in data
        assert set(data) == {"characters", "sidekicks"}
        assert "Aldo" in data["characters"]
        assert "Tetra" in data["sidekicks"]

    def test_get_entities_excludes_sidekick_character_name_overlap(self, test_client, stub_driver):
        """Stale duplicate Character nodes must not appear in the hero picker."""
        stub_driver.execute_query = AsyncMock(
            return_value=(
                [
                    {"name": "Aldo", "type": "Character"},
                    {"name": "Mare", "type": "Character"},
                    {"name": "Mare", "type": "Sidekick"},
                ],
                None,
                None,
            )
        )

        data = test_client.get("/api/entities").json()

        assert data["characters"] == ["Aldo"]
        assert data["sidekicks"] == ["Mare"]

    def test_get_entities_empty_db(self, test_client, stub_driver):
        """GET /api/entities returns empty lists when Neo4j returns no records."""
        stub_driver.execute_query = AsyncMock(return_value=([], None, None))
        response = test_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert data["characters"] == []
        assert data["sidekicks"] == []


class TestPostQuery:
    def test_post_query_returns_sse_fragment(self, test_client):
        """POST /api/query returns HTML fragment containing sse-connect URL (WEB-02, two-phase pattern)."""
        response = test_client.post(
            "/api/query",
            json={"query": "best blunt team", "roster": ["Aldo", "Ciel"], "owned_sidekicks": ["Tetra"]},
        )
        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "/api/stream/" in response.text

    def test_post_query_stores_job_in_state(self, test_client):
        """POST /api/query stores job payload in app.state.jobs keyed by UUID."""
        from src.web.app import app as web_app
        response = test_client.post(
            "/api/query",
            json={"query": "best team", "roster": ["Aldo"], "owned_sidekicks": ["Tetra"]},
        )
        assert response.status_code == 200
        # The job should be stored (at least one entry)
        assert len(web_app.state.jobs) >= 1
        assert any(job.get("owned_sidekicks") == ["Tetra"] for job in web_app.state.jobs.values())
