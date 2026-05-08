import logging

logger = logging.getLogger(__name__)

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
            self._trader = XtQuantTrader()
            result = self._trader.connect(path)
            self._connected = (result == 0)
            return self._connected
        except Exception:
            logger.exception("Failed to connect to QMT")
            return False

    def disconnect(self):
        self._connected = False
        self._trader = None


def get_connector() -> QMTConnector:
    return QMTConnector()
