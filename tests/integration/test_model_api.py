"""Integration tests for model API endpoints: config save/retrieve, signal generation validation."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.src.main import app
    with TestClient(app) as c:
        yield c


class TestModelListAPI:
    def test_list_models_returns_array(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(m["model_name"] == "ma_cross" for m in data)

    def test_model_detail_returns_metadata(self, client):
        resp = client.get("/api/models/ma_cross/detail")
        assert resp.status_code == 200
        data = resp.json()
        assert "model" in data
        assert data["model"]["model_name"] == "ma_cross"
        assert data["model"]["display_name"] == "双均线模型"
        assert isinstance(data["model"]["default_params"], dict)

    def test_nonexistent_model_returns_404(self, client):
        resp = client.get("/api/models/ghost_model/detail")
        assert resp.status_code == 404


class TestModelConfigAPI:
    def test_save_and_retrieve_config(self, client):
        resp = client.put("/api/models/ma_cross/config", json={
            "stock_code": "000001.SZ",
            "params": {"short": 5, "long": 20},
            "position_pct": 80,
            "time_range": "6m",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        detail = client.get("/api/models/ma_cross/detail").json()
        assert detail["config"]["stock_code"] == "000001.SZ"
        assert detail["config"]["position_pct"] == 80
        assert detail["config"]["time_range"] == "6m"

    def test_config_short_gte_long_returns_error(self, client):
        resp = client.put("/api/models/ma_cross/config", json={
            "stock_code": "000001.SZ",
            "params": {"short": 20, "long": 5},
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 400
        assert "快线" in resp.json()["error"]

    def test_config_invalid_position_pct(self, client):
        resp = client.put("/api/models/ma_cross/config", json={
            "stock_code": "000001.SZ",
            "params": {"short": 5, "long": 20},
            "position_pct": 0,
            "time_range": "1y",
        })
        assert resp.status_code == 400

    def test_config_invalid_time_range(self, client):
        resp = client.put("/api/models/ma_cross/config", json={
            "stock_code": "000001.SZ",
            "params": {"short": 5, "long": 20},
            "position_pct": 100,
            "time_range": "2y",
        })
        assert resp.status_code == 400


class TestSignalGenerationValidation:
    def test_missing_stock_code(self, client):
        resp = client.post("/api/models/ma_cross/signals", json={
            "stock_code": "",
            "short": 5,
            "long": 20,
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 400
        assert "标的" in resp.json()["error"]

    def test_short_gte_long(self, client):
        resp = client.post("/api/models/ma_cross/signals", json={
            "stock_code": "000001.SZ",
            "short": 50,
            "long": 20,
            "position_pct": 100,
            "time_range": "1y",
        })
        assert resp.status_code == 400
        assert "快线" in resp.json()["error"]

    def test_invalid_position_pct(self, client):
        resp = client.post("/api/models/ma_cross/signals", json={
            "stock_code": "000001.SZ",
            "short": 5,
            "long": 20,
            "position_pct": 101,
            "time_range": "1y",
        })
        assert resp.status_code == 400

    def test_invalid_time_range(self, client):
        resp = client.post("/api/models/ma_cross/signals", json={
            "stock_code": "000001.SZ",
            "short": 5,
            "long": 20,
            "position_pct": 100,
            "time_range": "bad",
        })
        assert resp.status_code == 400


class TestModelPages:
    def test_models_page_renders(self, client):
        resp = client.get("/models")
        assert resp.status_code == 200
        assert "双均线" in resp.text
        assert "ma_cross" in resp.text

    def test_model_detail_page_renders(self, client):
        resp = client.get("/models/ma_cross")
        assert resp.status_code == 200
        assert "双均线模型" in resp.text
        assert "ma-chart" in resp.text

    def test_nonexistent_model_page_returns_404(self, client):
        resp = client.get("/models/ghost_model")
        assert resp.status_code == 404
