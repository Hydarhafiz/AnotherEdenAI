"""Unit tests for GET / (index page) — WEB-01."""
import pytest


class TestIndexPage:
    def test_index_returns_html(self, test_client):
        """GET / returns 200 with HTML content-type."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_query_form(self, test_client):
        """GET / page contains the query form targeting /api/query."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "hx-post" in response.text or "/api/query" in response.text

    def test_index_contains_sidekick_picker(self, test_client):
        """GET / page exposes sidekick ownership selection alongside characters."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "Sidekicks" in response.text
        assert "sidekick-list" in response.text
        assert "panel-grastas" not in response.text
        assert "grasta-list" not in response.text

    def test_index_busts_cached_frontend_bundle_after_picker_change(self, test_client):
        """GET / references the app.js version without stale Grasta ownership code."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "/static/app.js?v=6" in response.text
