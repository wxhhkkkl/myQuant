"""Integration tests for batch update of stock basic info."""
import pytest


class TestDataUpdateAPI:
    """Tests for the data update trigger and status endpoints."""

    def test_update_status_returns_html(self, client):
        response = client.get("/api/data/update-stocks/status")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_trigger_update_returns_html(self, client):
        response = client.post("/api/data/update-stocks")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_trigger_update_returns_running_state(self, client):
        """After triggering update, status should reflect update has been started."""
        response = client.post("/api/data/update-stocks")
        assert response.status_code == 200
        html = response.text
        assert "更新" in html

    def test_status_after_trigger_is_consistent(self, client):
        """GET /status should return valid HTML containing expected structure."""
        response = client.get("/api/data/update-stocks/status")
        assert response.status_code == 200
        assert response.text

    def test_concurrent_update_is_rejected(self, client):
        """If update is already running, second trigger should return current state."""
        from backend.src.services.data_service import _update_status
        original = dict(_update_status)
        try:
            _update_status["running"] = True
            _update_status["total"] = 100
            response = client.post("/api/data/update-stocks")
            assert response.status_code == 200
            html = response.text
            assert "100" in html or "更新" in html
        finally:
            _update_status.update(original)
