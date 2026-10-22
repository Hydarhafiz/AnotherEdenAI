"""Unit tests for GET /api/entities and POST /api/query — WEB-02."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.sse import ServerSentEvent


class TestGetEntities:
    async def test_get_entities_returns_characters_and_sidekicks(self, async_client, stub_driver):
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
        response = await async_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert "sidekicks" in data
        assert set(data) == {"characters", "sidekicks"}
        assert "Aldo" in data["characters"]
        assert "Tetra" in data["sidekicks"]

    async def test_get_entities_excludes_sidekick_character_name_overlap(self, async_client, stub_driver):
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

        data = (await async_client.get("/api/entities")).json()

        assert data["characters"] == ["Aldo"]
        assert data["sidekicks"] == ["Mare"]

    async def test_get_entities_empty_db(self, async_client, stub_driver):
        """GET /api/entities returns empty lists when Neo4j returns no records."""
        stub_driver.execute_query = AsyncMock(return_value=([], None, None))
        response = await async_client.get("/api/entities")
        assert response.status_code == 200
        data = response.json()
        assert data["characters"] == []
        assert data["sidekicks"] == []


class TestPostQuery:
    async def test_malformed_query_request_returns_validation_details(self, async_client):
        response = await async_client.post("/api/query", json={
            "query": 42, "roster": ["Aldo"], "mode": "exploratory",
        })
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["body", "query"]

    async def test_post_query_returns_sse_fragment(self, async_client):
        """POST /api/query returns HTML fragment containing sse-connect URL (WEB-02, two-phase pattern)."""
        response = await async_client.post(
            "/api/query",
            json={"query": "best blunt team", "roster": ["Aldo", "Ciel"], "owned_sidekicks": ["Tetra"]},
        )
        assert response.status_code == 200
        assert "sse-connect" in response.text
        assert "/api/stream/" in response.text

    async def test_post_query_stores_job_in_state(self, async_client):
        """POST /api/query stores job payload in app.state.jobs keyed by UUID."""
        from src.web.app import app as web_app
        response = await async_client.post(
            "/api/query",
            json={"query": "best team", "roster": ["Aldo"], "owned_sidekicks": ["Tetra"]},
        )
        assert response.status_code == 200
        # The job should be stored (at least one entry)
        assert len(web_app.state.jobs) >= 1
        assert any(job.get("owned_sidekicks") == ["Tetra"] for job in web_app.state.jobs.values())

    @pytest.mark.parametrize("mode", ["production", "exploratory"])
    async def test_frontend_payload_survives_post_and_stream(
        self, async_client, frontend_payload, mode
    ):
        from src.web.app import app as web_app

        payload = frontend_payload(
            mode=mode, query="Prefer sustain" if mode == "production" else "Graph question",
            roster=["Toova", "Yuna"], sidekicks=["Tetra"],
        )
        response = await async_client.post("/api/query", json=payload)
        assert response.status_code == 200
        job_id, stored = next(iter(web_app.state.jobs.items()))
        assert stored.items() >= payload.items()
        assert f'/api/stream/{job_id}' in response.text
        captured = {}

        async def stream(**kwargs):
            captured.update(kwargs)
            yield ServerSentEvent(data="", event="done")

        with patch("src.web.routes.api.pipeline_sse_generator", stream):
            response = await async_client.get(f"/api/stream/{job_id}")
        assert response.status_code == 200
        assert "event: done" in response.text
        for key, value in payload.items():
            assert captured[key] == value

    async def test_invalid_and_reused_stream_jobs_return_not_found(self, async_client):
        from fastapi import HTTPException
        from src.web.app import app as web_app
        from src.web.routes.api import stream_job

        posted = await async_client.post("/api/query", json={
            "query": "Graph question", "roster": ["Aldo"], "mode": "exploratory",
        })
        assert posted.status_code == 200
        stream_url = posted.text.split('sse-connect="', 1)[1].split('"', 1)[0]
        job_id = stream_url.rsplit("/", 1)[-1]

        async def stream(**kwargs):
            yield ServerSentEvent(data="", event="done")

        with patch("src.web.routes.api.pipeline_sse_generator", stream):
            first = await async_client.get(stream_url)
        assert first.status_code == 200
        assert "event: done" in first.text
        assert job_id not in web_app.state.jobs

        request = MagicMock()
        request.app.state.jobs = web_app.state.jobs
        for missing_id in (job_id, "not-a-job"):
            with pytest.raises(HTTPException) as error:
                [event async for event in stream_job(missing_id, request, driver=MagicMock())]
            assert error.value.status_code == 404
        assert job_id not in web_app.state.jobs
