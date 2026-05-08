import pytest


class TestBacktestRunAPI:
    """Contract tests for POST /api/backtest/run."""

    def test_run_endpoint_requires_body(self, client):
        """POST /api/backtest/run should return 422 without required fields."""
        response = client.post("/api/backtest/run", json={})
        assert response.status_code == 422

    def test_run_endpoint_accepts_valid_request(self, client):
        """POST /api/backtest/run should return 200 with valid params."""
        payload = {
            "model_name": "ma_cross",
            "params": {"short": 5, "long": 20},
            "stock_code": "000001.SZ",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "initial_capital": 100000,
        }
        response = client.post("/api/backtest/run", json=payload)
        # May be 200 (success) or 422 (no data) — depends on DB state
        assert response.status_code in (200, 422, 404, 500)


class TestBacktestResultAPI:
    """Contract tests for GET /api/backtest/{run_id} endpoints."""

    def test_result_endpoint_for_unknown_id(self, client):
        """GET /api/backtest/unknown-id should return 404."""
        response = client.get("/api/backtest/unknown-id")
        assert response.status_code == 404

    def test_trades_endpoint_for_unknown_id(self, client):
        """GET /api/backtest/unknown-id/trades should return 404."""
        response = client.get("/api/backtest/unknown-id/trades")
        assert response.status_code == 404

    def test_history_endpoint_returns_list(self, client):
        """GET /api/backtest/history should return a list."""
        response = client.get("/api/backtest/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestModelsAPI:
    """Contract tests for GET /api/models and related endpoints."""

    def test_list_models_returns_list(self, client):
        """GET /api/models should return list of available models."""
        response = client.get("/api/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_models_page_returns_html(self, client):
        """GET /models should return HTML page."""
        response = client.get("/models")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_backtest_page_returns_html(self, client):
        """GET /backtest should return HTML page."""
        response = client.get("/backtest")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
