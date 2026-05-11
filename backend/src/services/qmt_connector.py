import logging
import os
import sys

from backend.src.config import QMT_PATH, QMT_SITE_PACKAGES_PATH

logger = logging.getLogger(__name__)

# Ensure QMT xtquant is on Python path
if QMT_PATH:
    qmt_bin = os.path.normpath(QMT_PATH)
    if qmt_bin not in sys.path:
        sys.path.append(qmt_bin)

# Broker versions put xtquant in Lib/site-packages
# Use append (not insert) so the venv's packages take priority over QMT's bundled dependencies
if QMT_SITE_PACKAGES_PATH:
    if QMT_SITE_PACKAGES_PATH not in sys.path:
        sys.path.append(QMT_SITE_PACKAGES_PATH)

try:
    from xtquant import xttrader
    HAS_QMT = True
except ImportError:
    xttrader = None
    HAS_QMT = False


class QMTConnector:
    """Singleton connection manager for QMT xttrader."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._trader = None
            cls._instance._connected = False
            cls._instance._accounts = None
        return cls._instance

    @property
    def trader(self):
        return self._trader

    def is_connected(self) -> bool:
        return self._connected

    def connect(self, path: str = None) -> bool:
        if not HAS_QMT:
            logger.warning("xtquant not available; QMT features disabled.")
            return False
        try:
            from xtquant.xttrader import XtQuantTrader
            qmt_path = path or os.path.join(QMT_PATH, "..", "userdata_mini")
            qmt_path = os.path.normpath(qmt_path)
            session_id = 123456
            self._trader = XtQuantTrader(qmt_path, session_id)
            # Broker version requires start() before connect()
            self._trader.start()
            result = self._trader.connect()
            self._connected = result == 0 or result is True
            if self._connected:
                self._accounts = self._trader.query_account_infos()
            else:
                logger.warning("QMT connect failed (result=%s). Is MiniQMT running and logged in?", result)
            return self._connected
        except Exception:
            logger.exception("Failed to connect to QMT")
            return False

    def disconnect(self):
        if self._trader:
            try:
                self._trader.stop()
            except Exception:
                pass
        self._connected = False
        self._trader = None
        self._accounts = None

    def get_accounts(self):
        """Return list of XtAccountInfo objects."""
        if not self._connected:
            return []
        return self._accounts or []

    def query_asset(self, account=None):
        """Query account asset. Uses first account if none specified."""
        if not self._connected or not self._trader:
            return None
        acc = account or (self._accounts[0] if self._accounts else None)
        if not acc:
            return None
        return self._trader.query_stock_asset(acc)

    def query_positions(self, account=None):
        """Query stock positions. Uses first account if none specified."""
        if not self._connected or not self._trader:
            return []
        acc = account or (self._accounts[0] if self._accounts else None)
        if not acc:
            return []
        return self._trader.query_stock_positions(acc) or []

    def query_orders(self, account=None):
        """Query stock orders. Uses first account if none specified."""
        if not self._connected or not self._trader:
            return []
        acc = account or (self._accounts[0] if self._accounts else None)
        if not acc:
            return []
        return self._trader.query_stock_orders(acc) or []


def get_connector() -> QMTConnector:
    return QMTConnector()
