"""Unit tests for GET / (index page) — WEB-01."""
import pytest


class TestIndexPage:
    def test_index_returns_html(self, test_client):
        """GET / returns 200 with HTML content-type."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_query_form(self, test_client):
        """GET / page contains the form wired to the existing query script."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert 'id="query-form"' in response.text
        assert 'src="/static/app.js?v=11"' in response.text

    def test_index_contains_sidekick_picker(self, test_client):
        """GET / page exposes sidekick ownership selection alongside characters."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "Sidekicks" in response.text
        assert "sidekick-list" in response.text
        assert "panel-grastas" not in response.text
        assert "grasta-list" not in response.text

    def test_index_busts_cached_frontend_bundle_after_picker_change(self, test_client):
        """GET / references the redesigned frontend bundle."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert "/static/app.js?v=11" in response.text

    def test_index_exposes_separate_workspaces_and_collapsible_guidance(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        page = response.text
        assert 'id="mode-boss"' in page and 'id="mode-graph"' in page
        assert 'id="recommendation-panel"' in page and 'id="graph-panel"' in page
        assert 'id="query-input"' in page and 'id="graph-query-input"' in page
        assert '<details class="instructions">' in page
        assert 'id="roster-count-badge"' in page and 'id="character-search"' in page
        assert 'id="query-submit"' in page
        assert 'id="results-description"' in page

    def test_index_shows_compact_quick_start_before_workspace(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        page = response.text
        assert '<ol class="quick-start" aria-label="Quick start">' in page
        assert page.index('class="quick-start"') < page.index('class="workspace-card"')
        assert page.index('class="workspace-card"') < page.index('class="instructions"')
