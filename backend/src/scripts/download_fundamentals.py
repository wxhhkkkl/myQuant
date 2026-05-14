"""
Download stock fundamental (valuation) data and store in SQLite.

Computes PE/PB/market_cap by combining:
  - xtdata Capital table (total shares)
  - daily_kline (latest close, 52-week high/low)
  - financial_reports (EPS from PerShareIndex, net_profit)

Usage:
  python -m backend.src.scripts.download_fundamentals
"""
import logging
import time as _time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _xtdata_value(data_cache: dict, code: str, table: str, col: str):
    """Get the latest value of a column from an xtdata financial table."""
    if code not in data_cache:
        return None
    df = data_cache[code].get(table)
    if df is None or df.empty:
        return None
    latest = df.loc[df["m_timetag"].idxmax()]
    val = latest.get(col)
    return float(val) if val and val == val else None


def _get_latest_financials(code: str) -> dict | None:
    """Get latest annual financial data from SQLite financial_reports."""
    from backend.src.db.sqlite import get_db
    with get_db() as conn:
        row = conn.execute("""
            SELECT report_period, eps, net_profit, roe, debt_ratio
            FROM financial_reports
            WHERE stock_code = ? AND report_type = 'annual'
            ORDER BY report_period DESC LIMIT 1
        """, (code,)).fetchone()
    return dict(row) if row else None


def _get_price_data(code: str) -> dict | None:
    """Get latest price and 52-week range from DuckDB daily_kline."""
    from backend.src.db.duckdb import db

    row = db.query("""
        SELECT close, trade_date
        FROM daily_kline
        WHERE stock_code = ?
        ORDER BY trade_date DESC LIMIT 1
    """, (code,)).fetchone()

    if not row:
        return None

    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    hl = db.query("""
        SELECT MAX(high), MIN(low)
        FROM daily_kline
        WHERE stock_code = ? AND trade_date >= ?
    """, (code, one_year_ago)).fetchone()

    return {
        "latest_price": row[0],
        "trade_date": str(row[1]),
        "high_52w": hl[0] if hl else None,
        "low_52w": hl[1] if hl else None,
    }


def _get_dividend_per_share(code: str, latest_price: float) -> float | None:
    """Get trailing-twelve-month dividend per share from xtdata, compute yield."""
    from backend.src.services.data_service import HAS_XTDATA
    if not HAS_XTDATA:
        return None
    try:
        from xtquant import xtdata
        df = xtdata.get_divid_factors(code)
        if df is None or df.empty:
            return None
        # interest column = dividend per share; take the most recent
        latest_div = float(df["interest"].iloc[-1])
        if latest_div > 0 and latest_price > 0:
            return round(latest_div / latest_price * 100, 2)
    except Exception:
        pass
    return None


def download_all():
    from backend.src.models.stock import Stock
    from backend.src.models.fundamental import StockFundamental
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        logger.warning("xtquant not available; skipping fundamentals download.")
        return

    from xtquant import xtdata

    StockFundamental.create_table()

    stocks = Stock.all_active()
    total = len(stocks)
    today = datetime.now().strftime("%Y-%m-%d")
    BATCH = 100
    inserted = 0

    logger.info(f"Computing fundamentals for {total} stocks...")

    for bi in range(0, total, BATCH):
        batch = stocks[bi:bi + BATCH]
        codes = [s["stock_code"] for s in batch]

        # Download Capital data via xtdata financial API
        xtdata.download_financial_data(codes)
        _time.sleep(2)
        data = xtdata.get_financial_data(codes)

        for s in batch:
            code = s["stock_code"]
            try:
                total_cap = _xtdata_value(data, code, "Capital", "total_capital")
                bps = _xtdata_value(data, code, "PershareIndex", "s_fa_bps")
                fin = _get_latest_financials(code)
                px = _get_price_data(code)

                if not px or not px["latest_price"]:
                    continue

                latest_price = px["latest_price"]

                market_cap = None
                if total_cap:
                    market_cap = round(latest_price * total_cap / 1e8, 2)  # 亿元

                pe_ratio = None
                if fin and fin["eps"] and fin["eps"] != 0:
                    pe_ratio = round(latest_price / fin["eps"], 2)

                pb_ratio = None
                if bps and bps > 0:
                    pb_ratio = round(latest_price / bps, 2)

                dividend_yield = _get_dividend_per_share(code, latest_price)

                eps = fin["eps"] if fin else None
                high_52w = px["high_52w"]
                low_52w = px["low_52w"]

                StockFundamental.upsert(
                    code=code, snap_date=today,
                    market_cap=market_cap,
                    pe_ratio=pe_ratio,
                    pb_ratio=pb_ratio,
                    eps=eps,
                    high_52w=high_52w,
                    low_52w=low_52w,
                    dividend_yield=dividend_yield,
                    book_value_per_share=bps,
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"Fundamentals failed for {code}: {e}")

        done = min(bi + BATCH, total)
        logger.info(f"Progress: {done}/{total} stocks, {inserted} with data")


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    download_all()


if __name__ == "__main__":
    main()
