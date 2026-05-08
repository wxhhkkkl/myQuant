"""
Quantitative model framework. First model: MaCross (MA5/MA20 crossover).
"""
import logging
from typing import Optional

from backend.src.db.duckdb import db

logger = logging.getLogger(__name__)


def calc_ma(values: list, window: int) -> list:
    """Calculate simple moving average. Returns list with None for first window-1 positions."""
    result = []
    running_sum = 0
    for i, v in enumerate(values):
        running_sum += v
        if i >= window:
            running_sum -= values[i - window]
            result.append(running_sum / window)
        elif i == window - 1:
            result.append(running_sum / window)
        else:
            result.append(None)
    return result


def detect_crossover(closes: list, ma_short: list, ma_long: list) -> list:
    """
    Detect MA crossover signals.
    Returns list of {"trade_date": str, "signal_type": "BUY"|"SELL", "price": float}.
    """
    signals = []
    for i in range(1, len(closes)):
        if None in (ma_short[i], ma_long[i], ma_short[i - 1], ma_long[i - 1]):
            continue
        # Golden cross: short MA crosses above long MA
        if ma_short[i - 1] <= ma_long[i - 1] and ma_short[i] > ma_long[i]:
            signals.append({"signal_type": "BUY", "price": closes[i], "index": i})
        # Death cross: short MA crosses below long MA
        elif ma_short[i - 1] >= ma_long[i - 1] and ma_short[i] < ma_long[i]:
            signals.append({"signal_type": "SELL", "price": closes[i], "index": i})
    return signals


class MaCrossModel:
    """Dual moving average crossover model (MA5/MA20)."""

    def __init__(self, short: int = 5, long: int = 20):
        if short >= long:
            raise ValueError(f"short window ({short}) must be less than long window ({long})")
        self.short = short
        self.long = long

    def generate_signals(self, kline_data: list) -> list:
        """Generate BUY/SELL signals from K-line data."""
        closes = [r["close"] for r in kline_data]
        ma_short = calc_ma(closes, self.short)
        ma_long = calc_ma(closes, self.long)
        return detect_crossover(closes, ma_short, ma_long)

    def scan_stock(self, stock_code: str) -> list:
        """Scan a single stock for the latest signal."""
        rows = db.query("""
            SELECT trade_date, close FROM daily_kline
            WHERE stock_code = ?
            ORDER BY trade_date DESC
            LIMIT ?
        """, (stock_code, self.long + 2)).fetchall()

        if len(rows) < self.long:
            return []

        rows = list(reversed(rows))
        closes = [r[1] for r in rows]
        dates = [str(r[0]) for r in rows]

        ma_short = calc_ma(closes, self.short)
        ma_long = calc_ma(closes, self.long)
        signals = detect_crossover(closes, ma_short, ma_long)

        for s in signals:
            s["trade_date"] = dates[s["index"]]

        return signals
