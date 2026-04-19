"""Shared fixtures for the web layer unit tests.

Mirrors tests/workflow/conftest.py pattern.
stub_driver uses AsyncMock for execute_query (web layer awaits it).
test_client overrides get_driver dependency so tests never touch Neo4j.
mock_admin_env sets ADMIN_KEY env var for admin tests.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.web.app import app
from src.web.dependencies import get_driver


@pytest.fixture
def stub_driver():
    """Neo4j driver mock. execute_query and close are AsyncMock (web layer awaits both)."""
    driver = MagicMock()
    driver.execute_query = AsyncMock(
        return_value=([{"name": "Aldo", "type": "Character"}], None, None)
    )
    driver.close = AsyncMock()
    return driver


@pytest.fixture
def test_client(stub_driver):
    """TestClient with get_driver dependency overridden to stub_driver.

    Also patches AsyncGraphDatabase.driver so lifespan does not connect to Neo4j.
    """
    with patch("src.web.app.AsyncGraphDatabase.driver", return_value=stub_driver):
        with TestClient(app) as client:
            # Override dependency so route handlers use stub_driver directly
            app.dependency_overrides[get_driver] = lambda: stub_driver
            yield client
            app.dependency_overrides.clear()


@pytest.fixture
def mock_admin_env(monkeypatch):
    """Set ADMIN_KEY to a known test value for admin endpoint tests."""
    monkeypatch.setenv("ADMIN_KEY", "test-secret-key")
    return "test-secret-key"
