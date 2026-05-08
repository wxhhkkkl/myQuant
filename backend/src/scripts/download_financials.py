"""
Download financial reports via xtdata and store in SQLite.
Usage: python -m backend.src.scripts.download_financials
"""
import logging

logger = logging.getLogger(__name__)


def download_for_stock(code: str):
    """Download financial report data for a single stock."""
    from backend.src.models.financial_report import FinancialReport
    from backend.src.services.data_service import HAS_XTDATA

    if not HAS_XTDATA:
        return

    from xtquant import xtdata
    try:
        reports = xtdata.get_financial_data(code)
        if not reports:
            return

        for period, items in reports.items():
            FinancialReport.upsert(
                code=code,
                period=period,
                revenue=items.get("revenue"),
                net_profit=items.get("net_profit"),
                roe=items.get("roe"),
                debt_ratio=items.get("debt_ratio"),
                eps=items.get("eps"),
                report_type=items.get("report_type"),
            )
    except Exception as e:
        logger.warning(f"Financial download failed for {code}: {e}")


def download_all():
    """Download financial reports for all active stocks."""
    from backend.src.models.stock import Stock

    stocks = Stock.all_active()
    logger.info(f"Downloading financial reports for {len(stocks)} stocks...")

    for i, s in enumerate(stocks):
        download_for_stock(s["stock_code"])
        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i + 1}/{len(stocks)} stocks")

    logger.info("Financial reports download complete.")


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    download_all()


if __name__ == "__main__":
    main()
