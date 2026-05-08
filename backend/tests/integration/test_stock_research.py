import pytest


class TestStockResearchFlow:
    """Integration test: full stock research flow."""

    def test_search_to_detail_navigation_flow(self, client):
        """User searches for a stock, then views its detail page."""
        # Step 1: Search
        search_resp = client.get("/api/stocks/search?q=000001")
        assert search_resp.status_code == 200

        # Step 2: Navigate to detail page
        detail_resp = client.get("/stocks/000001.SZ")
        assert detail_resp.status_code == 200
        assert "text/html" in detail_resp.headers.get("content-type", "")

    def test_stock_detail_tabs_all_render(self, client):
        """All four stock detail tabs should render successfully."""
        tabs = ["fundamentals", "financials", "sentiment", "sector"]

        for tab in tabs:
            response = client.get(f"/api/stocks/000001.SZ/{tab}")
            assert response.status_code == 200, f"Tab {tab} failed with {response.status_code}"
            assert "text/html" in response.headers.get("content-type", "")

    def test_ai_picks_endpoint_returns_html(self, client):
        """POST /api/stocks/ai-picks should return HTML with recommendations."""
        response = client.post("/api/stocks/ai-picks", json={
            "market": "all",
            "min_score": 60,
        })

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_watchlist_add_and_list_flow(self, client):
        """User adds a stock to watchlist, then lists watchlist."""
        add_resp = client.post("/api/watchlist/add", json={"stock_code": "000001.SZ"})
        assert add_resp.status_code in (200, 201)

        list_resp = client.get("/api/watchlist")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert isinstance(data, list)

    def test_watchlist_remove_flow(self, client):
        """User removes a stock from watchlist."""
        resp = client.delete("/api/watchlist/000001.SZ")
        assert resp.status_code == 200
