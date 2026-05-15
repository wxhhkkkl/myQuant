import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock xtquant before imports
sys.modules["xtquant"] = MagicMock()
sys.modules["xtquant.xttrader"] = MagicMock()
sys.modules["xtquant.xtdata"] = MagicMock()


class TestQMTConnector:
    """Unit tests for QMT connection manager."""

    def test_connector_is_singleton(self):
        """QMT connector should be a singleton."""
        from backend.src.services.qmt_connector import get_connector

        c1 = get_connector()
        c2 = get_connector()
        assert c1 is c2

    def test_connector_connect_method_exists(self):
        """Connector should have connect and disconnect methods."""
        from backend.src.services.qmt_connector import get_connector

        c = get_connector()
        assert hasattr(c, "connect")
        assert hasattr(c, "disconnect")

    @patch("backend.src.services.qmt_connector.HAS_QMT", True)
    def test_connect_calls_xttrader(self):
        """connect() should call xttrader connect."""
        from backend.src.services.qmt_connector import QMTConnector

        with patch("xtquant.xttrader.XtQuantTrader") as mock_trader:
            mock_trader.return_value.connect.return_value = 0
            c = QMTConnector()
            result = c.connect(path="C:/test")
            assert result is True


class TestTradeService:
    """Unit tests for trade execution service."""

    @patch("backend.src.services.trade_service.HAS_QMT", True)
    def test_place_order_returns_order_dict(self):
        """place_order() should return order dict with status."""
        from backend.src.services.trade_service import TradeService
        from unittest.mock import MagicMock

        svc = TradeService()
        svc._connector = MagicMock()
        svc._connector.is_connected.return_value = True
        svc._connector.submit_order.return_value = 12345

        result = svc.place_order("000001.SZ", "BUY", 12.5, 100)

        assert "order_id" in result
        assert result["stock_code"] == "000001.SZ"
        assert result["order_type"] == "BUY"
        assert result["status"] == "submitted"

    def test_place_order_requires_connection(self):
        """place_order() should raise when not connected."""
        from backend.src.services.trade_service import TradeService

        svc = TradeService()
        svc._connector = MagicMock()
        svc._connector.is_connected.return_value = False

        with pytest.raises(RuntimeError):
            svc.place_order("000001.SZ", "BUY", 12.5, 100)

    def test_connector_cancel_order(self):
        """QMTConnector.cancel_order() should call xttrader cancel."""
        from backend.src.services.qmt_connector import QMTConnector
        from unittest.mock import MagicMock

        c = QMTConnector()
        c._trader = MagicMock()
        c._connected = True

        result = c.cancel_order(42)

        c._trader.cancel_order_stock.assert_called_once_with(42)
        assert result is True
