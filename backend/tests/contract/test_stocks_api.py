import pytest


class TestStocksSearchAPI:
    """Contract tests for GET /api/stocks/search."""

    def test_search_returns_json_with_results(self, client):
        """Search endpoint should return JSON with results array."""
        response = client.get("/api/stocks/search?q=平安")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_empty_query_returns_empty(self, client):
        """Search with empty query should return empty list or error."""
        response = client.get("/api/stocks/search?q=")
        assert response.status_code in (200, 422)

    def test_search_nonexistent_stock_returns_empty(self, client):
        """Search for nonexistent stock should return empty list."""
        response = client.get("/api/stocks/search?q=ZZZZZZZZZ")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_by_stock_code(self, client):
        """Search by stock code should return matching results."""
        response = client.get("/api/stocks/search?q=000001")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStockDetailAPI:
    """Contract tests for stock detail HTMX endpoints."""

    def test_fundamentals_endpoint_returns_html(self, client):
        """GET /api/stocks/{code}/fundamentals should return HTML fragment."""
        response = client.get("/api/stocks/000001.SZ/fundamentals")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_financials_endpoint_returns_html(self, client):
        """GET /api/stocks/{code}/financials should return HTML fragment."""
        response = client.get("/api/stocks/000001.SZ/financials")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_sentiment_endpoint_returns_html(self, client):
        """GET /api/stocks/{code}/sentiment should return HTML fragment."""
        response = client.get("/api/stocks/000001.SZ/sentiment")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_sector_endpoint_returns_html(self, client):
        """GET /api/stocks/{code}/sector should return HTML fragment."""
        response = client.get("/api/stocks/000001.SZ/sector")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_detail_endpoints_return_404_for_unknown_stock(self, client):
        """Detail endpoints should return 404 for nonexistent stock code."""
        response = client.get("/api/stocks/ZZZZZZZ/fundamentals")
        assert response.status_code == 404

    def test_stocks_page_returns_html(self, client):
        """GET /stocks should return HTML page."""
        response = client.get("/stocks")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_stock_detail_page_returns_html(self, client):
        """GET /stocks/{code} should return HTML page."""
        response = client.get("/stocks/000001.SZ")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
