"""Unit tests for watchlist operations. Uses client fixture for DB setup."""
import pytest
from backend.src.models.watchlist import Watchlist


class TestWatchlist:
    """Tests for watchlist CRUD operations using seeded stock 000001.SZ."""

    def test_add_stock_to_watchlist(self, client):
        Watchlist.add("000001.SZ")
        assert Watchlist.contains("000001.SZ") is True

    def test_remove_stock_from_watchlist(self, client):
        Watchlist.add("000001.SZ")
        Watchlist.remove("000001.SZ")
        assert Watchlist.contains("000001.SZ") is False

    def test_add_duplicate_does_not_raise(self, client):
        Watchlist.add("000001.SZ")
        Watchlist.add("000001.SZ")
        assert Watchlist.contains("000001.SZ") is True

    def test_remove_nonexistent_does_not_raise(self, client):
        Watchlist.remove("ZZZZZZ.ZZ")

    def test_contains_nonexistent_returns_false(self, client):
        assert Watchlist.contains("ZZZZZZ.ZZ") is False

    def test_all_returns_list(self, client):
        result = Watchlist.all()
        assert isinstance(result, list)
        for item in result:
            assert "stock_code" in item
            assert "stock_name" in item

    def test_all_includes_stock_name(self, client):
        Watchlist.add("000001.SZ")
        result = Watchlist.all()
        codes = [r["stock_code"] for r in result]
        assert "000001.SZ" in codes
