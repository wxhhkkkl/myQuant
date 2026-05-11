"""Unit tests for get_stock_list_with_quotes function."""
import pytest
from backend.src.services.data_service import (
    get_stock_list_with_quotes, get_weekly_kline, get_monthly_kline,
)


class TestGetStockListWithQuotes:
    """Tests for paginated stock list with quotes."""

    def test_returns_valid_pagination_structure(self, client):
        """Returns list with valid pagination metadata."""
        result = get_stock_list_with_quotes(page=1, per_page=50)
        assert isinstance(result["stocks"], list)
        assert result["pagination"]["page"] == 1
        assert isinstance(result["pagination"]["total"], int)
        assert result["pagination"]["total_pages"] >= 1

    def test_pagination_structure(self):
        """Result includes correct pagination metadata."""
        result = get_stock_list_with_quotes(page=2, per_page=100)
        assert "stocks" in result
        assert "pagination" in result
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["per_page"] == 100

    def test_sort_by_valid_field_does_not_crash(self):
        """Sorting by any valid field should not raise an error."""
        for field in ["stock_code", "latest_price", "change_pct"]:
            result = get_stock_list_with_quotes(sort_by=field, sort_order="asc")
            assert "stocks" in result

    def test_sort_order_desc(self):
        """Descending sort order does not crash."""
        result = get_stock_list_with_quotes(sort_by="stock_code", sort_order="desc")
        assert "stocks" in result

    def test_keyword_filter(self):
        """Keyword filter does not crash."""
        result = get_stock_list_with_quotes(keyword="平安")
        assert "stocks" in result
        assert isinstance(result["pagination"]["total"], int)

    def test_watchlist_only_filter(self):
        """Watchlist-only filter does not crash."""
        result = get_stock_list_with_quotes(watchlist_only=True)
        assert "stocks" in result
        assert isinstance(result["pagination"]["total"], int)

    def test_stock_fields_structure(self):
        """Each stock dict has all required fields."""
        result = get_stock_list_with_quotes()
        for s in result["stocks"]:
            assert "stock_code" in s
            assert "stock_name" in s
            assert "latest_price" in s
            assert "change_pct" in s
            assert "in_watchlist" in s


class TestKlineAggregation:
    """Tests for weekly and monthly K-line aggregation."""

    def test_weekly_kline_returns_list(self):
        result = get_weekly_kline("000001.SZ", "2025-01-01", "2025-12-31")
        assert isinstance(result, list)
        for row in result:
            assert "trade_date" in row
            assert "open" in row
            assert "high" in row
            assert "low" in row
            assert "close" in row
            assert "volume" in row
            assert "amount" in row

    def test_monthly_kline_returns_list(self):
        result = get_monthly_kline("000001.SZ", "2025-01-01", "2025-12-31")
        assert isinstance(result, list)

    def test_weekly_kline_empty_for_nonexistent_code(self):
        result = get_weekly_kline("ZZZZZZ.ZZ", "2020-01-01", "2020-12-31")
        assert result == []

    def test_monthly_kline_empty_for_nonexistent_code(self):
        result = get_monthly_kline("ZZZZZZ.ZZ", "2020-01-01", "2020-12-31")
        assert result == []
