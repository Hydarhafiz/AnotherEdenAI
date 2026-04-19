"""Unit tests for POST /admin/refresh-data — WEB-05."""
import pytest
from unittest.mock import AsyncMock, patch


class TestAdminRefreshData:
    def test_refresh_data_valid_key(self, test_client, stub_driver, mock_admin_env):
        """POST /admin/refresh-data with correct X-Admin-Key returns 200 {"status": "ok"}."""
        with patch("src.web.routes.admin.run_etl", new_callable=AsyncMock) as mock_etl:
            response = test_client.post(
                "/admin/refresh-data",
                headers={"X-Admin-Key": mock_admin_env},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_etl.assert_called_once()

    def test_refresh_data_invalid_key(self, test_client, mock_admin_env):
        """POST /admin/refresh-data with wrong X-Admin-Key returns 403."""
        response = test_client.post(
            "/admin/refresh-data",
            headers={"X-Admin-Key": "definitely-wrong-key"},
        )
        assert response.status_code == 403

    def test_refresh_data_missing_key(self, test_client, mock_admin_env):
        """POST /admin/refresh-data with no X-Admin-Key header returns 403."""
        response = test_client.post("/admin/refresh-data")
        assert response.status_code == 403

    def test_refresh_data_etl_error_returns_error_json(self, test_client, stub_driver, mock_admin_env):
        """POST /admin/refresh-data returns {"status": "error"} when ETL raises."""
        with patch(
            "src.web.routes.admin.run_etl",
            new_callable=AsyncMock,
            side_effect=RuntimeError("scraper blocked"),
        ):
            response = test_client.post(
                "/admin/refresh-data",
                headers={"X-Admin-Key": mock_admin_env},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "error"
        assert "scraper blocked" in response.json()["message"]
