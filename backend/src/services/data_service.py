import logging
import sys
from datetime import datetime

from backend.src.db.duckdb import db
from backend.src.db.sqlite import get_db
from backend.src.config import QMT_PATH, QMT_SITE_PACKAGES_PATH

logger = logging.getLogger(__name__)

# Add QMT path to Python path so xtquant can be found
if QMT_PATH:
    import os as _os
    qmt_path = _os.path.normpath(QMT_PATH)
    if qmt_path not in sys.path:
        sys.path.append(qmt_path)
    # Some QMT installs have xtquant inside a sub-directory
    alt_path = _os.path.join(qmt_path, "xtquant")
    if _os.path.isdir(alt_path) and alt_path not in sys.path:
        sys.path.append(alt_path)

# Broker versions put xtquant in Lib/site-packages
# Use append (not insert) so the venv's packages take priority over QMT's bundled dependencies
if QMT_SITE_PACKAGES_PATH:
    if QMT_SITE_PACKAGES_PATH not in sys.path:
        sys.path.append(QMT_SITE_PACKAGES_PATH)

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


def get_stock_list_with_quotes(page=1, per_page=50, sort_by='stock_code',
                                sort_order='asc', keyword='', watchlist_only=False):
    """Return paginated stock list with latest price and change% from DuckDB."""
    # 1. Get all active stock codes (or filtered by keyword/watchlist)
    with get_db() as conn:
        where_clauses = []
        params = []
        if watchlist_only:
            where_clauses.append("stock_code IN (SELECT stock_code FROM watchlist)")
        else:
            where_clauses.append("is_active = 1")
        if keyword:
            where_clauses.append("(stock_code LIKE ? OR stock_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        where_sql = " AND ".join(where_clauses)
        count_sql = f"SELECT COUNT(*) FROM stocks WHERE {where_sql}"
        total = conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT stock_code, stock_name, industry, exchange, is_active "
            f"FROM stocks WHERE {where_sql} ORDER BY stock_code "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()
        stocks = [dict(r) for r in rows]

    if not stocks:
        return {"stocks": [], "pagination": {"page": page, "per_page": per_page, "total": total, "total_pages": max(1, (total + per_page - 1) // per_page)}}

    # 2. Get latest prices from DuckDB for visible stock codes
    codes = [s['stock_code'] for s in stocks]
    placeholders = ','.join(['?' for _ in codes])
    price_rows = db.query(f"""
        WITH latest AS (
            SELECT stock_code, close, trade_date,
                   ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date DESC) AS rn
            FROM daily_kline
            WHERE stock_code IN ({placeholders})
        )
        SELECT l.stock_code, l.close AS latest_price, l.trade_date,
               prev.close AS prev_close
        FROM latest l
        LEFT JOIN daily_kline prev
          ON l.stock_code = prev.stock_code
         AND prev.trade_date = (
             SELECT MAX(trade_date) FROM daily_kline
             WHERE stock_code = l.stock_code AND trade_date < l.trade_date
         )
        WHERE l.rn = 1
    """, codes).fetchall()
    price_map = {}
    for r in price_rows:
        prev = r[3] if r[3] and r[3] != 0 else None
        chg_pct = round((r[1] - prev) / prev * 100, 2) if prev and r[1] else None
        price_map[r[0]] = {"latest_price": r[1], "change_pct": chg_pct}

    # 3. Get watchlist status for visible codes
    wl_codes = set()
    with get_db() as conn:
        wl_rows = conn.execute(
            f"SELECT stock_code FROM watchlist WHERE stock_code IN ({placeholders})",
            codes
        ).fetchall()
        wl_codes = {r[0] for r in wl_rows}

    # 4. Merge and sort
    result = []
    for s in stocks:
        px = price_map.get(s['stock_code'], {})
        result.append({
            "stock_code": s['stock_code'],
            "stock_name": s['stock_name'],
            "latest_price": px.get("latest_price"),
            "change_pct": px.get("change_pct"),
            "in_watchlist": s['stock_code'] in wl_codes,
            "is_active": s.get('is_active', 1),
        })

    # Sort by the requested field
    sort_key_map = {
        "stock_code": lambda x: x["stock_code"],
        "latest_price": lambda x: x["latest_price"] or 0,
        "change_pct": lambda x: x["change_pct"] if x["change_pct"] is not None else float('-inf'),
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["stock_code"])
    reverse = sort_order == "desc"
    result.sort(key=key_fn, reverse=reverse)

    return {
        "stocks": result,
        "pagination": {
            "page": page, "per_page": per_page, "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }
    }


def get_weekly_kline(code: str, start: str, end: str) -> list:
    """Get weekly K-line aggregated from daily_kline."""
    rows = db.query("""
        SELECT
            date_trunc('week', trade_date)::DATE AS trade_date,
            stock_code,
            FIRST(open ORDER BY trade_date) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY trade_date) AS close,
            SUM(volume) AS volume,
            SUM(amount) AS amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        GROUP BY date_trunc('week', trade_date), stock_code
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


def get_monthly_kline(code: str, start: str, end: str) -> list:
    """Get monthly K-line aggregated from daily_kline."""
    rows = db.query("""
        SELECT
            date_trunc('month', trade_date)::DATE AS trade_date,
            stock_code,
            FIRST(open ORDER BY trade_date) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY trade_date) AS close,
            SUM(volume) AS volume,
            SUM(amount) AS amount
        FROM daily_kline
        WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
        GROUP BY date_trunc('month', trade_date), stock_code
        ORDER BY trade_date
    """, (code, start, end)).fetchall()

    return [
        {"trade_date": str(r[0]), "open": r[1], "high": r[2],
         "low": r[3], "close": r[4], "volume": r[5], "amount": r[6]}
        for r in rows
    ]


# --- Batch stock update state ---
import threading

_update_status = {"running": False, "total": 0, "success": 0, "fail": 0, "failed_codes": []}


def get_update_status() -> dict:
    return dict(_update_status)


def run_stock_update():
    """Background thread: download and upsert all A-share stock basic info."""
    if _update_status["running"]:
        return

    _update_status["running"] = True
    _update_status["total"] = 0
    _update_status["success"] = 0
    _update_status["fail"] = 0
    _update_status["failed_codes"] = []

    try:
        _ensure_xtdata()
        stocks = xtdata.get_stock_list_in_sector("沪深A股")
        _update_status["total"] = len(stocks)

        for code in stocks:
            try:
                info = xtdata.get_instrument_detail(code)
                name = info.get("InstrumentName", info.get("StockName", "")) if info else ""
                industry = info.get("Industry", "") if info else ""
                exchange = "SH" if code.startswith("6") else "SZ"
                list_date = info.get("ListDate", None) if info else None
                from backend.src.models.stock import Stock
                Stock.upsert(code, name, industry=industry, exchange=exchange, list_date=str(list_date) if list_date else None)
                _update_status["success"] += 1
            except Exception:
                _update_status["fail"] += 1
                _update_status["failed_codes"].append(code)
    finally:
        _update_status["running"] = False


def get_quote(code: str) -> dict:
    """Get latest market quote for a stock.

    Tries xtdata first for real-time data, falls back to latest daily_kline.
    """
    # Try xtdata real-time quote
    if HAS_XTDATA:
        try:
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'lastClose', 'lastPrice',
                            'volume', 'amount'],
                stock_list=[code],
                period='1d',
                start_time='',
                count=2
            )
            if data and code in data and len(data[code]) > 0:
                # xtdata returns dict of DataFrames keyed by field
                import pandas as pd
                last_price = float(data['lastPrice'].iloc[-1, 0]) if 'lastPrice' in data else None
                pre_close = float(data['lastClose'].iloc[-1, 0]) if 'lastClose' in data else None
                open_px = float(data['open'].iloc[-1, 0]) if 'open' in data else None
                high = float(data['high'].iloc[-1, 0]) if 'high' in data else None
                low = float(data['low'].iloc[-1, 0]) if 'low' in data else None
                volume = int(data['volume'].iloc[-1, 0]) if 'volume' in data else None
                amount = float(data['amount'].iloc[-1, 0]) if 'amount' in data else None

                if last_price and pre_close and pre_close != 0:
                    change_pct = round((last_price - pre_close) / pre_close * 100, 2)
                    change_amount = round(last_price - pre_close, 2)
                else:
                    change_pct = None
                    change_amount = None

                trade_date = str(data.index[-1]) if hasattr(data, 'index') and len(data.index) > 0 else None

                return {
                    "stock_code": code,
                    "latest_price": last_price,
                    "change_pct": change_pct,
                    "change_amount": change_amount,
                    "open": open_px,
                    "high": high,
                    "low": low,
                    "pre_close": pre_close,
                    "volume": volume,
                    "amount": amount,
                    "trade_date": trade_date,
                }
        except Exception as e:
            logger.warning(f"xtdata quote failed for {code}: {e}")

    # Fallback to latest daily_kline
    row = db.query("""
        SELECT trade_date, open, high, low, close, volume, amount
        FROM daily_kline
        WHERE stock_code = ?
        ORDER BY trade_date DESC LIMIT 1
    """, (code,)).fetchone()

    if not row:
        return {
            "stock_code": code, "latest_price": None,
            "change_pct": None, "change_amount": None,
            "open": None, "high": None, "low": None,
            "pre_close": None, "volume": None, "amount": None,
            "trade_date": None,
        }

    pre_row = db.query("""
        SELECT close FROM daily_kline
        WHERE stock_code = ? AND trade_date < ?
        ORDER BY trade_date DESC LIMIT 1
    """, (code, str(row[0]))).fetchone()

    pre_close = pre_row[0] if pre_row else None
    price = row[4]
    if price and pre_close and pre_close != 0:
        change_pct = round((price - pre_close) / pre_close * 100, 2)
        change_amount = round(price - pre_close, 2)
    else:
        change_pct = None
        change_amount = None

    return {
        "stock_code": code,
        "latest_price": price,
        "change_pct": change_pct,
        "change_amount": change_amount,
        "open": row[1],
        "high": row[2],
        "low": row[3],
        "pre_close": pre_close,
        "volume": row[5],
        "amount": row[6],
        "trade_date": str(row[0]),
    }


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
