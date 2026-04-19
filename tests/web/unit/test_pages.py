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
