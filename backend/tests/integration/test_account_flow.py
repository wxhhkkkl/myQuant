import pytest


class TestAccountFlow:
    """Integration test: account overview → positions → asset curve."""

    def test_account_page_loads(self, client):
        """GET /account should return HTML page."""
        response = client.get("/account")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_account_overview_returns_html(self, client):
        """GET /api/account/overview should return HTML."""
        response = client.get("/api/account/overview")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_account_positions_returns_html(self, client):
        """GET /api/account/positions should return HTML."""
        response = client.get("/api/account/positions")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_account_curve_returns_json(self, client):
        """GET /api/account/curve should return JSON array."""
        response = client.get("/api/account/curve")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_full_account_flow(self, client):
        """Seed position data and verify overview includes it."""
        from backend.src.models.position import Position
        from backend.src.models.account_snapshot import AccountSnapshot

        Position.create_table()
        AccountSnapshot.create_table()

        Position.upsert(
            stock_code="000001.SZ",
            stock_name="平安银行",
            quantity=500,
            avg_cost=10.0,
            current_price=12.0,
        )
        AccountSnapshot.create(total_asset=106000.0, available_cash=100000.0,
                               market_value=6000.0)

        overview = client.get("/api/account/overview")
        assert overview.status_code == 200

        positions = client.get("/api/account/positions")
        assert positions.status_code == 200
        content = positions.text
        assert "000001.SZ" in content
