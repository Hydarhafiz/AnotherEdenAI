"""Unit tests for src/web/app.py — lifespan and app.state (WEB-04)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.web.app import app


class TestLifespan:
    def test_lifespan_creates_driver(self):
        """app.state.driver is set during TestClient context (lifespan runs)."""
        mock_driver = MagicMock()
        mock_driver.close = AsyncMock()  # lifespan awaits driver.close() on shutdown
        with patch("src.web.app.AsyncGraphDatabase.driver", return_value=mock_driver):
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                assert hasattr(app.state, "driver")
                assert app.state.driver is mock_driver

    def test_lifespan_creates_jobs_dict(self):
        """app.state.jobs is initialized as empty dict during lifespan."""
        mock_driver = MagicMock()
        mock_driver.close = AsyncMock()  # lifespan awaits driver.close() on shutdown
        with patch("src.web.app.AsyncGraphDatabase.driver", return_value=mock_driver):
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                assert hasattr(app.state, "jobs")
                assert isinstance(app.state.jobs, dict)
