import logging
from datetime import datetime

from backend.src.db.duckdb import db
from backend.src.db.sqlite import get_db

logger = logging.getLogger(__name__)

# Optional imports — QMT xtdata may not be installed
try:
    from xtquant import xtdata
    HAS_XTDATA = True
except ImportError:
    xtdata = None
    HAS_XTDATA = False
    logger.warning("xtquant not available; xtdata features disabled.")

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    ak = None
    HAS_AKSHARE = False
    logger.warning("akshare not available; supplement features disabled.")


def _ensure_xtdata():
    if not HAS_XTDATA:
        raise RuntimeError("xtquant is not installed.")


def get_stock_list() -> list:
    """Return all A-share stocks with stock_code and stock_name."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT stock_code, stock_name FROM stocks WHERE is_active = 1"
        ).fetchall()
    return [dict(r) for r in rows]


def get_kline(code: str, start: str, end: str) -> list:
    """Get daily K-line data for a stock in date range. Returns list of dicts."""
    if start > end:
        raise ValueError(f"start date {start} > end date {end}")

    rows = db.query("""
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


def get_financials(code: str) -> list:
    """Get financial reports for a stock."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT report_period, revenue, net_profit, roe, debt_ratio, eps, report_type
            FROM financial_reports
            WHERE stock_code = ?
            ORDER BY report_period DESC
            LIMIT 8
        """, (code,)).fetchall()
    return [dict(r) for r in rows]


def get_sector_info(code: str) -> dict:
    """Get industry/sector classification for a stock."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT industry, sub_industry FROM stocks WHERE stock_code = ?",
            (code,)
        ).fetchone()
    if row:
        return {"industry": row["industry"], "sub_industry": row["sub_industry"],
                "stock_code": code}
    return None


def get_valuation(code: str) -> dict:
    """Get PE/PB/valuation snapshot for a stock."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT pe_ratio, pb_ratio, market_cap, eps, high_52w, low_52w
            FROM stock_fundamentals
            WHERE stock_code = ?
            ORDER BY snap_date DESC LIMIT 1
        """, (code,)).fetchone()
    return dict(row) if row else None


def get_news(code: str, limit: int = 20) -> list:
    """Get sentiment news for a stock."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, summary, source, pub_time, sentiment
            FROM sentiment_news
            WHERE stock_code = ?
            ORDER BY pub_time DESC
            LIMIT ?
        """, (code, limit)).fetchall()
    return [dict(r) for r in rows]
