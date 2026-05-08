import logging
from datetime import datetime, time
from concurrent.futures import ThreadPoolExecutor

from backend.src.services.qmt_connector import get_connector, HAS_QMT

logger = logging.getLogger(__name__)

_TRADING_START = time(9, 30)
_TRADING_END = time(15, 0)


def _is_trading_time() -> bool:
    now = datetime.now().time()
    if datetime.now().weekday() >= 5:
        return False
    return _TRADING_START <= now <= _TRADING_END

_executor = ThreadPoolExecutor(max_workers=4)


class TradeService:
    """Trade execution service wrapping QMT xttrader."""

    def __init__(self):
        self._connector = get_connector()

    def _require_connection(self):
        if not self._connector.is_connected():
            raise RuntimeError("QMT not connected")

    def place_order(self, stock_code: str, order_type: str,
                    price: float, quantity: int, signal_id: int = None) -> dict:
        """Submit an order. Returns dict with order_id and status."""
        self._require_connection()
        order_id = self._connector.trader.order_stock(
            stock_code, order_type, price, quantity
        )
        from backend.src.models.order import Order
        Order.create_table()
        db_id = Order.create(stock_code, order_type, price, quantity, signal_id)
        return {
            "order_id": order_id or db_id,
            "stock_code": stock_code,
            "order_type": order_type,
            "status": "submitted",
        }

    def cancel_order(self, order_id: int) -> bool:
        """Cancel a submitted order."""
        self._require_connection()
        self._connector.trader.cancel_order_stock(order_id)
        return True

    def scan_and_signal(self, model, stocks: list):
        """Run model on subscribed stocks and generate trade signals."""
        if not _is_trading_time():
            logger.info("Outside trading hours; skipping signal scan.")
            return

        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        for stock_code in stocks:
            try:
                signals = model.run(stock_code)
                for sig in signals:
                    TradeSignal.create(
                        stock_code=stock_code,
                        model_name=model.name,
                        signal_type=sig["signal_type"],
                        signal_price=sig["price"],
                        signal_reason=f"{model.name} crossover at index {sig['index']}",
                    )
            except Exception:
                logger.exception("Signal scan failed for %s", stock_code)
