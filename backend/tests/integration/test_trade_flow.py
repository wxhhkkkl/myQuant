import pytest


class TestTradeFlow:
    """Integration test: signal → confirm → order flow."""

    def test_trading_page_loads(self, client):
        """GET /trading should return HTML page."""
        response = client.get("/trading")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_list_signals_returns_html(self, client):
        """GET /api/signals should return HTML."""
        response = client.get("/api/signals")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_confirm_nonexistent_signal_returns_404(self, client):
        """POST /api/signals/99999/confirm should return 404."""
        response = client.post("/api/signals/99999/confirm")
        assert response.status_code == 404

    def test_dismiss_nonexistent_signal_returns_404(self, client):
        """POST /api/signals/99999/dismiss should return 404."""
        response = client.post("/api/signals/99999/dismiss")
        assert response.status_code == 404

    def test_list_orders_returns_html(self, client):
        """GET /api/orders should return HTML."""
        response = client.get("/api/orders")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_create_order_requires_body(self, client):
        """POST /api/orders should return 422 without required fields."""
        response = client.post("/api/orders", json={})
        assert response.status_code == 422

    def test_cancel_nonexistent_order_returns_404(self, client):
        """DELETE /api/orders/99999 should return 404."""
        response = client.delete("/api/orders/99999")
        assert response.status_code == 404

    def test_full_signal_lifecycle(self, client):
        """Create a signal, confirm it, then create an order."""
        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        sig_id = TradeSignal.create(
            stock_code="000001.SZ",
            model_name="ma_cross",
            signal_type="BUY",
            signal_price=12.5,
            signal_reason="Integration test signal",
        )

        # Confirm the signal
        resp = client.post(f"/api/signals/{sig_id}/confirm")
        assert resp.status_code == 200

        # Create order from the confirmed signal
        resp2 = client.post("/api/orders", json={
            "stock_code": "000001.SZ",
            "order_type": "BUY",
            "price": 12.5,
            "quantity": 100,
            "signal_id": sig_id,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert "order_id" in data or "id" in data
