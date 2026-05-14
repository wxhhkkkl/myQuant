"""
Download A-share stock list and sector classification via xtdata.
Usage: python -m backend.src.scripts.init_data
"""
import logging
from backend.src.models.log import setup_logging
from backend.src.db.migrate import run_migrations

logger = logging.getLogger(__name__)


def init_stock_list():
    """Download stock list and populate stocks table."""
    from backend.src.models.stock import Stock
    from backend.src.services.data_service import HAS_XTDATA, HAS_AKSHARE

    Stock.create_table()

    # Use akshare as primary source; xtdata get_stock_list_in_sector
    # can block indefinitely on first run.
    if HAS_AKSHARE:
        try:
            logger.info("Fetching stock list from akshare...")
            _save_stocks_from_akshare()
            return
        except Exception as e:
            logger.warning(f"akshare stock list failed: {e}")

    logger.warning("No data source available for stock list.")


def _save_stocks_from_xtdata(a_list):
    from backend.src.models.stock import Stock
    from xtquant import xtdata
    count = 0
    for code in a_list:
        try:
            info = xtdata.get_instrument_detail(code)
            if info:
                Stock.upsert(
                    code=code,
                    name=info.get("InstrumentName", ""),
                    exchange="SH" if code.startswith("6") else "SZ",
                    list_date=info.get("OpenDate", ""),
                )
                count += 1
        except Exception as e:
            logger.warning(f"Failed to upsert {code}: {e}")

    logger.info(f"Initialized {count} stocks.")


def _save_stocks_from_akshare():
    """Fallback: fetch A-share list from akshare."""
    from backend.src.db.sqlite import get_db
    import akshare as ak

    df = ak.stock_zh_a_spot_em()
    rows = []
    for _, row in df.iterrows():
        code = str(row.get("代码", "")).strip()
        name = str(row.get("名称", "")).strip()
        if not code or not name:
            continue
        exchange = "SH" if code.startswith("6") else "SZ"
        rows.append((code, name, exchange, "", "", ""))

    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_code VARCHAR(10) PRIMARY KEY,
                stock_name VARCHAR(50),
                exchange VARCHAR(10),
                industry VARCHAR(50),
                sub_industry VARCHAR(50),
                sub_sub_industry VARCHAR(50),
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.executemany("""
            INSERT INTO stocks (stock_code, stock_name, exchange, industry, sub_industry, sub_sub_industry)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(stock_code) DO UPDATE SET
                stock_name = excluded.stock_name,
                exchange = excluded.exchange
        """, rows)
    logger.info(f"Initialized {len(rows)} stocks from akshare.")


def init_sectors():
    """Download sector classification and update stocks table."""
    from backend.src.models.stock import Stock
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        return

    from xtquant import xtdata
    # Map of sector name → (industry, sub_industry) for common xtdata sectors
    sectors = {
        "银行": ("银行", "银行"),
        "证券": ("非银金融", "证券"),
        "保险": ("非银金融", "保险"),
        "房地产": ("房地产", "房地产开发"),
        "白酒": ("食品饮料", "白酒"),
    }

    for sector_name, (industry, sub) in sectors.items():
        try:
            codes = xtdata.get_stock_list_in_sector(sector_name)
            for code in codes:
                Stock.upsert(code, "", industry, sub)
        except Exception:
            pass


def main():
    setup_logging()
    run_migrations()
    logger.info("Starting stock list initialization...")
    init_stock_list()
    init_sectors()
    logger.info("Done.")


if __name__ == "__main__":
    main()
