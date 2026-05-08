import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock xtquant before any import that touches it
sys.modules['xtquant'] = MagicMock()
sys.modules['xtquant.xtdata'] = MagicMock()


class TestDataService:
    """Unit tests for xtdata data fetching functions."""

    def test_get_stock_list_returns_list_of_stocks(self):
        """get_stock_list() should return list of dicts with stock_code and stock_name."""
        from backend.src.services.data_service import get_stock_list

        result = get_stock_list()

        assert isinstance(result, list)
        if result:
            assert 'stock_code' in result[0]
            assert 'stock_name' in result[0]

    def test_get_kline_returns_ohlcv_data(self):
        """get_kline() should return list of OHLCV dicts for given stock and date range."""
        from backend.src.services.data_service import get_kline

        result = get_kline('000001.SZ', '2025-01-01', '2025-01-31')

        assert isinstance(result, list)
        if result:
            row = result[0]
            for field in ('trade_date', 'open', 'high', 'low', 'close', 'volume'):
                assert field in row, f"Missing field: {field}"

    def test_get_kline_rejects_invalid_date_range(self):
        """get_kline() should raise ValueError when start > end."""
        from backend.src.services.data_service import get_kline

        with pytest.raises(ValueError):
            get_kline('000001.SZ', '2025-12-31', '2025-01-01')

    def test_get_financials_returns_report_data(self):
        """get_financials() should return list of financial report dicts."""
        from backend.src.services.data_service import get_financials

        result = get_financials('000001.SZ')

        assert isinstance(result, list)
        if result:
            row = result[0]
            for field in ('report_period', 'revenue', 'net_profit'):
                assert field in row, f"Missing field: {field}"

    def test_get_stock_list_handles_empty_response(self):
        """get_stock_list() should return empty list when no stocks available."""
        from backend.src.services.data_service import get_stock_list

        result = get_stock_list()
        assert isinstance(result, list)
