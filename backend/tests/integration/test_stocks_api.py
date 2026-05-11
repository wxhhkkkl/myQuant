"""Integration tests for stock list and detail API endpoints."""
import pytest


class TestStockListAPI:
    """Tests for the stock list API endpoints."""

    def test_stocks_page_returns_html(self, client):
        response = client.get("/stocks")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_stock_list_api_returns_json(self, client):
        response = client.get("/api/stocks/list")
        assert response.status_code == 200
        data = response.json()
        assert "stocks" in data
        assert "pagination" in data
        assert isinstance(data["stocks"], list)

    def test_stock_list_api_pagination_params(self, client):
        response = client.get(
            "/api/stocks/list?page=1&per_page=10&sort_by=stock_code&sort_order=asc"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 10

    def test_stock_list_api_keyword_filter(self, client):
        response = client.get("/api/stocks/list?keyword=%E5%B9%B3%E5%AE%89")
        assert response.status_code == 200

    def test_stock_list_api_watchlist_only(self, client):
        response = client.get("/api/stocks/list?watchlist_only=true")
        assert response.status_code == 200

    def test_stock_list_contains_seeded_stock(self, client):
        """Seeded stock 000001.SZ should appear in list."""
        response = client.get("/api/stocks/list")
        assert response.status_code == 200
        data = response.json()
        codes = [s["stock_code"] for s in data["stocks"]]
        assert "000001.SZ" in codes

    def test_stock_table_component_returns_html(self, client):
        response = client.get("/stocks/table")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_stock_table_respects_sort(self, client):
        response = client.get("/stocks/table?sort_by=latest_price&sort_order=desc")
        assert response.status_code == 200

    def test_stock_table_respects_watchlist_filter(self, client):
        response = client.get("/stocks/table?watchlist_only=true")
        assert response.status_code == 200


class TestStockDetailAPI:
    """Tests for stock detail page API endpoints."""

    def test_stock_detail_page_returns_html(self, client):
        response = client.get("/stocks/000001.SZ")
        assert response.status_code == 200

    def test_stock_kline_api(self, client):
        response = client.get("/api/stocks/000001.SZ/kline")
        assert response.status_code == 200
        data = response.json()
        assert "stock_code" in data
        assert "data" in data

    def test_stock_kline_api_with_daily_period(self, client):
        response = client.get("/api/stocks/000001.SZ/kline?period=daily")
        assert response.status_code == 200

    def test_stock_kline_api_with_weekly_period(self, client):
        response = client.get("/api/stocks/000001.SZ/kline?period=weekly")
        assert response.status_code == 200

    def test_stock_kline_api_with_monthly_period(self, client):
        response = client.get("/api/stocks/000001.SZ/kline?period=monthly")
        assert response.status_code == 200

    def test_stock_quote_api(self, client):
        response = client.get("/api/stocks/000001.SZ/quote")
        assert response.status_code == 200
        data = response.json()
        assert "stock_code" in data
        assert "latest_price" in data

    def test_stock_kline_view_component(self, client):
        response = client.get("/stocks/000001.SZ/kline-view")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_stock_quote_view_component(self, client):
        response = client.get("/stocks/000001.SZ/quote-view")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestSearchAPI:
    """Tests for stock search."""

    def test_search_by_code_finds_seeded_stock(self, client):
        response = client.get("/api/stocks/search?q=000001")
        assert response.status_code == 200
        results = response.json()
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["stock_code"] == "000001.SZ"

    def test_search_by_name_finds_seeded_stock(self, client):
        response = client.get("/api/stocks/search?q=%E5%B9%B3%E5%AE%89")
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0

    def test_search_nonexistent_returns_empty(self, client):
        response = client.get("/api/stocks/search?q=ZZZZZZ")
        assert response.status_code == 200
        assert response.json() == []
