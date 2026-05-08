"""Daily incremental data sync orchestration script.

Runs:
  1. K-line increment (latest trading day via QMT xtdata)
  2. Valuation/PE/PB refresh (via akshare)
  3. News/sentiment fetch (via akshare)

Wired to APScheduler in production; can also be run manually:
  python -m backend.src.scripts.daily_sync
"""

import logging
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def sync_kline_increment():
    """Download latest K-line data for all active stocks."""
    from backend.src.services.data_service import get_stock_list, get_kline

    stocks = get_stock_list()
    if not stocks:
        logger.warning("No stocks found; run init_data.py first.")
        return

    today = date.today()
    start = (today - timedelta(days=7)).isoformat()
    end = today.isoformat()

    count = 0
    for stock in stocks:
        code = stock.get("stock_code", stock) if isinstance(stock, dict) else stock
        try:
            kline = get_kline(code, start, end)
            if kline:
                count += 1
        except Exception:
            logger.debug("K-line sync failed for %s", code)

    logger.info("K-line increment: %d stocks updated.", count)


def sync_valuation():
    """Refresh PE/PB/valuation data for all active stocks."""
    from backend.src.services.data_service import get_stock_list, get_valuation

    stocks = get_stock_list()
    if not stocks:
        return

    count = 0
    for stock in stocks:
        code = stock.get("stock_code", stock) if isinstance(stock, dict) else stock
        try:
            val = get_valuation(code)
            if val:
                count += 1
        except Exception:
            logger.debug("Valuation sync failed for %s", code)

    logger.info("Valuation refresh: %d stocks updated.", count)


def sync_news():
    """Fetch latest news/sentiment for stocks with active positions."""
    from backend.src.services.data_service import get_news
    from backend.src.models.position import Position

    positions = Position.all()
    if not positions:
        logger.info("No positions; skipping news sync.")
        return

    count = 0
    for pos in positions:
        try:
            news = get_news(pos["stock_code"], limit=5)
            if news:
                count += 1
        except Exception:
            logger.debug("News sync failed for %s", pos["stock_code"])

    logger.info("News sync: %d stocks updated.", count)


def run_daily_sync():
    logger.info("Starting daily sync...")
    sync_kline_increment()
    sync_valuation()
    sync_news()
    logger.info("Daily sync complete.")


if __name__ == "__main__":
    run_daily_sync()
