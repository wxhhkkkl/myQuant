"""
Download A-share stock list and sector classification via xtdata.
Usage: python -m backend.src.scripts.init_data
"""
import logging
from backend.src.models.log import setup_logging
from backend.src.db.migrate import run_migrations

logger = logging.getLogger(__name__)


def init_stock_list():
    """Download stock list from xtdata and populate stocks table."""
    from backend.src.models.stock import Stock
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        logger.warning("xtquant not available; skipping stock list download.")
        return

    from xtquant import xtdata
    Stock.create_table()

    # Download A-share stock list from xtdata
    a_list = xtdata.get_stock_list_in_sector("沪深A股")
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
