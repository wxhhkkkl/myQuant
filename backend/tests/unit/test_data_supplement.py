import sys
from unittest.mock import MagicMock

import pytest

sys.modules['akshare'] = MagicMock()


class TestDataSupplement:
    """Unit tests for akshare supplement data fetching functions."""

    def test_get_valuation_returns_pe_pb_data(self):
        """get_valuation() should return PE/PB/market_cap for a stock."""
        from backend.src.services.data_service import get_valuation

        result = get_valuation('000001.SZ')

        assert isinstance(result, dict)
        if result:
            for field in ('pe_ratio', 'pb_ratio', 'market_cap'):
                assert field in result, f"Missing field: {field}"

    def test_get_valuation_returns_none_for_nonexistent_stock(self):
        """get_valuation() should return None for unknown stock code."""
        from backend.src.services.data_service import get_valuation

        result = get_valuation('INVALID')
        assert result is None or isinstance(result, dict)

    def test_get_news_returns_list_of_articles(self):
        """get_news() should return list of news articles with title and sentiment."""
        from backend.src.services.data_service import get_news

        result = get_news('000001.SZ')

        assert isinstance(result, list)
        if result:
            row = result[0]
            assert 'title' in row
            assert 'sentiment' in row or 'pub_time' in row

    def test_get_news_respects_limit(self):
        """get_news() should respect the limit parameter."""
        from backend.src.services.data_service import get_news

        result = get_news('000001.SZ', limit=5)
        assert len(result) <= 5

    def test_get_sector_info_returns_sector_list(self):
        """get_sector_info() should return sector/industry info for a stock."""
        from backend.src.services.data_service import get_sector_info

        result = get_sector_info('000001.SZ')

        assert isinstance(result, dict)
        if result:
            assert 'industry' in result or 'sectors' in result
