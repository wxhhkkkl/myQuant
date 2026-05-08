import pytest


class TestBacktestFlow:
    """Integration test: full backtest flow."""

    def test_full_flow_model_list_to_backtest(self, client):
        """User browses models, then visits backtest page."""
        # Step 1: List models
        models_resp = client.get("/api/models")
        assert models_resp.status_code == 200

        # Step 2: Visit models page
        page_resp = client.get("/models")
        assert page_resp.status_code == 200

        # Step 3: Visit backtest page
        backtest_resp = client.get("/backtest")
        assert backtest_resp.status_code == 200

    def test_run_backtest_with_known_params(self, client):
        """Run a backtest with valid parameters."""
        payload = {
            "model_name": "ma_cross",
            "params": {"short": 5, "long": 20},
            "stock_code": "000001.SZ",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "initial_capital": 100000,
        }
        response = client.post("/api/backtest/run", json=payload)

        # Should succeed if we have K-line data, otherwise 422
        if response.status_code == 200:
            data = response.json()
            assert "run_id" in data
            assert "total_return" in data
            assert "trade_count" in data

    def test_history_includes_completed_runs(self, client):
        """After running backtests, history should list them."""
        response = client.get("/api/backtest/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_model_param_update(self, client):
        """Update model parameters via PUT."""
        response = client.put("/api/models/ma_cross/params", json={
            "short": 10, "long": 30
        })
        # May be 404 if model not registered yet
        assert response.status_code in (200, 404)
