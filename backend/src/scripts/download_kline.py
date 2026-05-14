"""
Download historical daily K-line data and store in DuckDB.
Data sources: xtdata (QMT) primary, akshare fallback.

Usage:
  python -m backend.src.scripts.download_kline                    # full download
  python -m backend.src.scripts.download_kline --increment        # incremental only
  python -m backend.src.scripts.download_kline 2025-01-01         # from date
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _code_to_symbol(code: str) -> str:
    """Convert stock code like 600519.SH to akshare symbol 600519."""
    return code.replace(".SH", "").replace(".SZ", "")


def download_all(start_date: str = "2020-01-01", end_date: str = None, increment: bool = False):
    """Download K-line for all active A-share stocks."""
    from backend.src.models.stock import Stock
    from backend.src.db.duckdb import db
    from backend.src.db.duckdb_schema import init_schema
    from backend.src.services.data_service import HAS_XTDATA, HAS_AKSHARE

    init_schema()

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    stocks = Stock.all_active()
    logger.info(f"Downloading K-line for {len(stocks)} stocks from {start_date} to {end_date}"
                f"{' (incremental)' if increment else ''}...")

    # Probe xtdata with first stock; fall back to akshare if it fails
    use_xtdata = False
    if HAS_XTDATA:
        try:
            from xtquant import xtdata
            start_d = start_date.replace("-", "")
            end_d = end_date.replace("-", "")
            data = xtdata.get_market_data_ex(
                [], [stocks[0]["stock_code"]], period="1d",
                start_time=start_d, end_time=end_d,
            )
            if data is not None and stocks[0]["stock_code"] in data and data[stocks[0]["stock_code"]] is not None:
                use_xtdata = True
        except Exception:
            pass

    if use_xtdata:
        logger.info("Using xtdata for K-line download.")
        _download_via_xtdata(stocks, start_date, end_date, increment)
    elif HAS_AKSHARE:
        logger.info("Using akshare for K-line download.")
        _download_via_akshare(stocks, start_date, end_date, increment)
    else:
        logger.warning("No data source available for K-line download.")


def _download_via_akshare(stocks, start_date: str, end_date: str, increment: bool):
    """Download K-line via akshare (no QMT required)."""
    import time as _time
    import pandas as pd
    from backend.src.db.duckdb import db
    import akshare as ak

    start_fmt = start_date.replace("-", "")
    end_fmt = end_date.replace("-", "")

    # Drop index for faster bulk insert
    db.execute("DROP INDEX IF EXISTS idx_kline_code")

    frames = []
    for i, s in enumerate(stocks):
        code = s["stock_code"]
        symbol = _code_to_symbol(code)

        if increment:
            last_row = db.query(
                "SELECT MAX(trade_date) FROM daily_kline WHERE stock_code = ?",
                [code]
            ).fetchone()
            if last_row and last_row[0]:
                last_date = str(last_row[0]).replace("-", "")
                if last_date >= end_fmt:
                    continue
                start_fmt = last_date

        for attempt in range(3):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily",
                    start_date=start_fmt, end_date=end_fmt, adjust="qfq",
                )
                if df is None or df.empty:
                    break

                mapped = pd.DataFrame({
                    "trade_date": df["日期"].astype(str).str[:10],
                    "stock_code": code,
                    "stock_name": s.get("stock_name", ""),
                    "open": df.get("开盘", 0),
                    "high": df.get("最高", 0),
                    "low": df.get("最低", 0),
                    "close": df.get("收盘", 0),
                    "volume": df.get("成交量", 0).fillna(0).astype("int64"),
                    "amount": df.get("成交额", 0).fillna(0).astype("int64"),
                })
                frames.append(mapped)
                break
            except Exception as e:
                if attempt < 2:
                    _time.sleep(0.5 * (attempt + 1))
                else:
                    logger.warning(f"K-line download failed for {code}: {e}")

        # Flush every 100 stocks
        if len(frames) >= 100:
            _flush_frames(frames)
            frames.clear()

        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i + 1}/{len(stocks)} stocks")

        _time.sleep(0.6)

    if frames:
        _flush_frames(frames)

    # Recreate index
    db.execute("CREATE INDEX IF NOT EXISTS idx_kline_code ON daily_kline(stock_code)")
    _log_summary(stocks)


def _flush_frames(frames):
    """Bulk-insert accumulated DataFrames into DuckDB."""
    import pandas as pd
    from backend.src.db.duckdb import db

    combined = pd.concat(frames, ignore_index=True)
    db.write_conn.register('batch_data', combined)
    db.execute("""INSERT OR IGNORE INTO daily_kline
                  (trade_date, stock_code, stock_name,
                   open, high, low, close, volume, amount)
                  SELECT * FROM batch_data""")
    db.write_conn.unregister('batch_data')


def _download_via_xtdata(stocks, start_date: str, end_date: str, increment: bool):
    """Download K-line via xtdata (requires QMT client running).

    Batched: trigger downloads, wait, batch-fetch, then bulk-insert via DataFrame.
    """
    import time as _time
    import pandas as pd
    from backend.src.db.duckdb import db
    from xtquant import xtdata

    start_d = start_date.replace("-", "")
    end_d = end_date.replace("-", "")
    total = len(stocks)
    BATCH = 50

    # Drop index before bulk load for faster inserts
    db.execute("DROP INDEX IF EXISTS idx_kline_code")

    inserted_rows = 0
    done = 0
    t0 = _time.time()

    for bi in range(0, total, BATCH):
        batch = stocks[bi:bi + BATCH]
        codes = [s["stock_code"] for s in batch]

        # Trigger async downloads
        for s in batch:
            code = s["stock_code"]
            s_d = start_d
            if increment:
                last_row = db.query(
                    "SELECT MAX(trade_date) FROM daily_kline WHERE stock_code = ?",
                    [code]
                ).fetchone()
                if last_row and last_row[0]:
                    last_d = str(last_row[0]).replace("-", "")
                    if last_d >= end_d:
                        continue
                    s_d = last_d
            xtdata.download_history_data(code, "1d", s_d, end_d)

        # Wait for downloads to complete
        _time.sleep(20)

        # Batch fetch all data
        data = xtdata.get_market_data_ex([], codes, "1d", start_d, end_d)

        # Build one DataFrame per stock, then bulk insert entire batch
        frames = []
        for s in batch:
            code = s["stock_code"]
            if data is None or code not in data or data[code] is None:
                continue
            df = data[code]
            if df.empty:
                continue
            df = df.copy()
            df.index = df.index.astype(str)
            df['trade_date'] = df.index.map(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:8]}")
            df['stock_code'] = code
            df['stock_name'] = s.get("stock_name", "")
            df['volume'] = df['volume'].fillna(0).astype('int64')
            df['amount'] = df['amount'].fillna(0).astype('int64')
            frames.append(df[['trade_date', 'stock_code', 'stock_name',
                              'open', 'high', 'low', 'close', 'volume', 'amount']])
            inserted_rows += len(df)
            done += 1

        if frames:
            combined = pd.concat(frames, ignore_index=True)
            db.write_conn.register('batch_data', combined)
            db.execute("""INSERT OR IGNORE INTO daily_kline
                          (trade_date, stock_code, stock_name,
                           open, high, low, close, volume, amount)
                          SELECT * FROM batch_data""")
            db.write_conn.unregister('batch_data')

        elapsed = _time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 999
        logger.info(f"  {done}/{total} stocks, {inserted_rows} rows, "
                    f"{rate:.1f} st/s, elapsed {elapsed:.0f}s, ETA {eta:.0f}s")

    # Recreate index
    db.execute("CREATE INDEX IF NOT EXISTS idx_kline_code ON daily_kline(stock_code)")

    logger.info(f"Download done: {done}/{total} stocks, {inserted_rows} rows "
                f"in {_time.time() - t0:.0f}s")
    _log_summary(stocks)


def _log_summary(stocks):
    from backend.src.db.duckdb import db
    total_rows = db.query("SELECT COUNT(*) FROM daily_kline").fetchone()[0]
    codes_with_data = db.query(
        "SELECT COUNT(DISTINCT stock_code) FROM daily_kline"
    ).fetchone()[0]
    logger.info(
        f"K-line download complete. {codes_with_data}/{len(stocks)} stocks, "
        f"{total_rows} rows total."
    )


def main():
    import sys
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()

    increment = False
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--increment" in sys.argv:
        increment = True

    start = args[0] if len(args) > 0 else "2020-01-01"
    end = args[1] if len(args) > 1 else None
    download_all(start, end, increment=increment)


if __name__ == "__main__":
    main()
