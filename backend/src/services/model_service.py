"""
Quantitative model framework. First model: MaCross (MA5/MA20 crossover).
"""
import logging
from typing import Optional

from backend.src.db.duckdb import db

logger = logging.getLogger(__name__)


def calc_ma(values: list, window: int) -> list:
    """Calculate simple moving average. None values are skipped — positions with None get None MA."""
    result = [None] * len(values)
    valid_count = 0
    running_sum = 0.0
    for i, v in enumerate(values):
        if v is None:
            continue
        valid_count += 1
        running_sum += v
        if valid_count > window:
            # Find the window-th previous valid value to subtract
            to_drop = _nth_prev_valid(values, i, window)
            if to_drop is not None:
                running_sum -= to_drop
            result[i] = running_sum / window
        elif valid_count == window:
            result[i] = running_sum / window
    return result


def _nth_prev_valid(values, end_idx, n):
    """Return the nth previous non-None value before end_idx, or None."""
    count = 0
    for j in range(end_idx - 1, -1, -1):
        if values[j] is not None:
            count += 1
            if count == n:
                return values[j]
    return None


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

        rows = [r for r in rows if r[1] is not None]
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

    def scan_full_range(self, stock_code: str, time_range: str = "1y") -> dict:
        """Scan a stock over a full time range and return kline, MA series, and signals."""
        from datetime import datetime, timedelta

        range_days = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = range_days.get(time_range, 365)
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = db.query("""
            SELECT trade_date, open, high, low, close
            FROM daily_kline
            WHERE stock_code = ? AND trade_date >= ?
            ORDER BY trade_date
        """, (stock_code, start_date)).fetchall()

        if len(rows) < self.long:
            return {"error": f"数据不足：需要至少 {self.long} 个交易日，实际 {len(rows)} 个"}

        dates = [str(r[0]) for r in rows]
        opens = [float(r[1]) if r[1] else None for r in rows]
        highs = [float(r[2]) if r[2] else None for r in rows]
        lows = [float(r[3]) if r[3] else None for r in rows]
        closes = [float(r[4]) if r[4] else None for r in rows]

        ma_short = calc_ma(closes, self.short)
        ma_long = calc_ma(closes, self.long)
        signals = detect_crossover(closes, ma_short, ma_long)

        for s in signals:
            s["trade_date"] = dates[s["index"]]
            s["signal_price"] = closes[s["index"]]

        kline_data = []
        for i in range(len(dates)):
            kline_data.append([dates[i], opens[i], closes[i], lows[i], highs[i]])

        ma_short_series = []
        ma_long_series = []
        for i in range(len(dates)):
            if ma_short[i] is not None:
                ma_short_series.append([dates[i], round(ma_short[i], 2)])
            if ma_long[i] is not None:
                ma_long_series.append([dates[i], round(ma_long[i], 2)])

        return {
            "kline": kline_data,
            "ma_short": ma_short_series,
            "ma_long": ma_long_series,
            "signals": signals,
            "performance": compute_performance(signals),
        }


def compute_performance(signals: list) -> dict:
    """Compute basic performance stats from a list of BUY/SELL signals.

    Returns dict with total_signals, trade_pairs, win_rate (%), cumulative_return (%).
    """
    total = len(signals)
    if total == 0:
        return {"total_signals": 0, "trade_pairs": 0, "win_rate": 0.0, "cumulative_return": 0.0}

    cumulative_return = 0.0
    wins = 0
    pairs = 0
    buy_price = None

    for s in signals:
        if s["signal_type"] == "BUY":
            buy_price = s["signal_price"]
        elif s["signal_type"] == "SELL" and buy_price is not None:
            ret = (s["signal_price"] - buy_price) / buy_price * 100
            cumulative_return += ret
            if ret > 0:
                wins += 1
            pairs += 1
            buy_price = None

    win_rate = (wins / pairs * 100) if pairs > 0 else 0.0

    return {
        "total_signals": total,
        "trade_pairs": pairs,
        "win_rate": round(win_rate, 1),
        "cumulative_return": round(cumulative_return, 2),
    }
