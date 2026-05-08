"""
Download historical daily K-line data via xtdata and store in DuckDB.
Usage: python -m backend.src.scripts.download_kline
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def download_all(start_date: str = "2020-01-01", end_date: str = None):
    """Download K-line for all active A-share stocks."""
    from backend.src.models.stock import Stock
    from backend.src.db.duckdb import db
    from backend.src.db.duckdb_schema import init_schema
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        logger.warning("xtquant not available; skipping K-line download.")
        return

    from xtquant import xtdata
    init_schema()

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    stocks = Stock.all_active()
    logger.info(f"Downloading K-line for {len(stocks)} stocks from {start_date} to {end_date}...")

    for i, s in enumerate(stocks):
        code = s["stock_code"]
        try:
            data = xtdata.get_market_data_ex(
                [], [code], period="1d",
                start_time=start_date, end_time=end_date,
            )
            if data is None or code not in data:
                continue

            df = data[code]
            if df.empty:
                continue

            for ts, row in df.iterrows():
                trade_date = ts.strftime("%Y-%m-%d") if hasattr(ts, 'strftime') else str(ts)[:10]
                db.execute("""
                    INSERT OR IGNORE INTO daily_kline
                        (trade_date, stock_code, stock_name, open, high, low, close, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_date, code, s.get("stock_name", ""),
                    float(row.get("open", 0)), float(row.get("high", 0)),
                    float(row.get("low", 0)), float(row.get("close", 0)),
                    int(row.get("volume", 0)), int(row.get("amount", 0)),
                ))
        except Exception as e:
            logger.warning(f"K-line download failed for {code}: {e}")

        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i + 1}/{len(stocks)} stocks")

    logger.info(f"K-line download complete.")


def main():
    import sys
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    start = sys.argv[1] if len(sys.argv) > 1 else "2020-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else None
    download_all(start, end)


if __name__ == "__main__":
    main()
