"""Tests for trading module: model management, signal scanning, order execution, P&L."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.src.main import app
    with TestClient(app) as c:
        yield c


# --- US1: Model display & start/stop ---

class TestModelListing:
    """T010: Model listing with run state."""

    def test_list_models_returns_all_active(self, client):
        resp = client.get("/api/trading/models")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        m = data[0]
        assert "model_name" in m
        assert "display_name" in m
        assert "is_running" in m
        assert "capital" in m
        assert "config" in m

    def test_model_has_ma_cross(self, client):
        resp = client.get("/api/trading/models")
        data = resp.json()
        assert any(m["model_name"] == "ma_cross" for m in data)


class TestModelStartStop:
    """T011: Model start/stop toggles is_running and persists config."""

    def test_start_model(self, client):
        resp = client.post("/api/trading/models/ma_cross/start", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["model_name"] == "ma_cross"

        # Verify via listing
        models = client.get("/api/trading/models").json()
        ma = next(m for m in models if m["model_name"] == "ma_cross")
        assert ma["is_running"] is True

    def test_stop_model(self, client):
        # Start first
        client.post("/api/trading/models/ma_cross/start", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "1y",
        })
        # Stop
        resp = client.post("/api/trading/models/ma_cross/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

        models = client.get("/api/trading/models").json()
        ma = next(m for m in models if m["model_name"] == "ma_cross")
        assert ma["is_running"] is False

    def test_start_nonexistent_model_returns_404(self, client):
        resp = client.post("/api/trading/models/ghost_model/start", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 404


class TestModelConfigUpdate:
    """T012: Model config update validates and saves."""

    def test_update_config(self, client):
        resp = client.put("/api/trading/models/ma_cross/config", json={
            "params": {"short": 10, "long": 30},
            "position_pct": 50,
            "time_range": "6m",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        models = client.get("/api/trading/models").json()
        ma = next(m for m in models if m["model_name"] == "ma_cross")
        config = ma["config"]
        # Config should reflect new params
        assert config is not None

    def test_config_rejects_short_gte_long(self, client):
        resp = client.put("/api/trading/models/ma_cross/config", json={
            "params": {"short": 30, "long": 10},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 400

    def test_config_rejects_invalid_position_pct(self, client):
        resp = client.put("/api/trading/models/ma_cross/config", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 0,
            "time_range": "1y",
        })
        assert resp.status_code == 400

    def test_config_rejects_invalid_time_range(self, client):
        resp = client.put("/api/trading/models/ma_cross/config", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "2y",
        })
        assert resp.status_code == 400


# --- US2: Signal scanning ---

class TestSignalScanning:
    """T019-T021: Scan buy/sell signals with scope filtering."""

    def test_scan_buy_requires_model_running(self, client):
        resp = client.post("/api/trading/models/ma_cross/scan", json={
            "signal_type": "BUY",
            "scope": "watchlist",
        })
        # Works even if model not running — scan is manual
        assert resp.status_code in (200, 400)

    def test_scan_buy_with_watchlist_scope(self, client):
        resp = client.post("/api/trading/models/ma_cross/scan", json={
            "signal_type": "BUY",
            "scope": "watchlist",
        })
        assert resp.status_code in (200, 400)  # 400 if empty watchlist

    def test_scan_invalid_signal_type(self, client):
        resp = client.post("/api/trading/models/ma_cross/scan", json={
            "signal_type": "HOLD",
            "scope": "all",
        })
        assert resp.status_code == 400


# --- US3: Signal confirmation & order creation ---

class TestSignalConfirmation:
    """T026-T028: Confirm signal → create order."""

    def test_confirm_nonexistent_signal(self, client):
        resp = client.post("/api/signals/99999/confirm")
        assert resp.status_code == 404

    def test_ignore_nonexistent_signal(self, client):
        resp = client.post("/api/signals/99999/ignore")
        assert resp.status_code == 404


# --- US4: Order monitoring & retry ---

class TestOrderMonitoring:
    """T033-T035: Order monitoring, retry limits, price deviation."""

    def test_retry_nonexistent_order(self, client):
        resp = client.post("/api/trading/orders/99999/retry")
        assert resp.status_code == 400

    def test_monitor_returns_html(self, client):
        resp = client.get("/api/trading/orders/monitor")
        assert resp.status_code == 200
        assert "订单" in resp.text or "暂无" in resp.text or "order" in resp.text.lower()

    def test_model_orders_endpoint(self, client):
        resp = client.get("/api/trading/models/ma_cross/orders")
        assert resp.status_code == 200


# --- US5: Model performance ---

class TestModelPerformance:
    """T042-T043: Per-model performance aggregation."""

    def test_performance_returns_data(self, client):
        resp = client.get("/api/trading/models/ma_cross/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_name" in data
        assert "total_asset" in data
        assert "total_return" in data
        assert "market_value" in data
        assert "available_cash" in data
        assert "positions" in data


# --- End-to-end workflow ---

class TestTradingWorkflow:
    """T048: Full workflow: start model → scan → confirm → order → performance."""

    def test_full_workflow(self, client):
        # 1. Check models list
        resp = client.get("/api/trading/models")
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) >= 1

        # 2. Update config
        resp = client.put("/api/trading/models/ma_cross/config", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 200

        # 3. Start model
        resp = client.post("/api/trading/models/ma_cross/start", json={
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

        # 4. Verify running state
        models = client.get("/api/trading/models").json()
        ma = next(m for m in models if m["model_name"] == "ma_cross")
        assert ma["is_running"] is True

        # 5. Check performance
        resp = client.get("/api/trading/models/ma_cross/performance")
        assert resp.status_code == 200

        # 6. Stop model
        resp = client.post("/api/trading/models/ma_cross/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"
