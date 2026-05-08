"""
Download PE/PB/valuation snapshots and news via akshare.
Usage: python -m backend.src.scripts.sync_supplement
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sync_valuation():
    """Download PE/PB/valuation data for active stocks via akshare."""
    from backend.src.models.stock import Stock
    from backend.src.models.fundamental import StockFundamental
    from backend.src.services.data_service import HAS_AKSHARE

    if not HAS_AKSHARE:
        logger.warning("akshare not available; skipping valuation sync.")
        return

    import akshare as ak
    stocks = Stock.all_active()
    today = datetime.now().strftime("%Y-%m-%d")

    for i, s in enumerate(stocks):
        code = s["stock_code"]
        try:
            df = ak.stock_individual_info_em(symbol=code.replace(".SZ", "").replace(".SH", ""))
            if df.empty:
                continue
            info = dict(zip(df["item"], df["value"]))
            StockFundamental.upsert(
                code=code,
                snap_date=today,
                market_cap=float(info.get("总市值", 0)) / 1e8 if info.get("总市值") else None,
                pe_ratio=float(info.get("市盈率-动态", 0)) if info.get("市盈率-动态") else None,
                pb_ratio=float(info.get("市净率", 0)) if info.get("市净率") else None,
                eps=float(info.get("基本每股收益", 0)) if info.get("基本每股收益") else None,
                high_52w=float(info.get("52周最高", 0)) if info.get("52周最高") else None,
                low_52w=float(info.get("52周最低", 0)) if info.get("52周最低") else None,
            )
        except Exception as e:
            logger.warning(f"Valuation sync failed for {code}: {e}")

        if (i + 1) % 50 == 0:
            logger.info(f"Valuation progress: {i + 1}/{len(stocks)} stocks")

    logger.info("Valuation sync complete.")


def sync_news():
    """Download latest news for active stocks via akshare."""
    from backend.src.models.stock import Stock
    from backend.src.models.sentiment_news import SentimentNews
    from backend.src.services.data_service import HAS_AKSHARE

    if not HAS_AKSHARE:
        logger.warning("akshare not available; skipping news sync.")
        return

    import akshare as ak
    stocks = Stock.all_active()

    for i, s in enumerate(stocks[:50]):  # Limit to 50 stocks for news
        code = s["stock_code"]
        try:
            df = ak.stock_news_em(symbol=code.replace(".SZ", "").replace(".SH", ""))
            if df.empty:
                continue
            for _, row in df.head(10).iterrows():
                SentimentNews.insert(
                    code=code,
                    title=str(row.get("title", "")),
                    summary=str(row.get("content", ""))[:500] if row.get("content") else None,
                    source=row.get("source"),
                    url=row.get("url"),
                    pub_time=str(row.get("pub_time", "")),
                )
        except Exception as e:
            logger.warning(f"News sync failed for {code}: {e}")

        if (i + 1) % 10 == 0:
            logger.info(f"News progress: {i + 1}/{min(len(stocks), 50)} stocks")

    logger.info("News sync complete.")


def main():
    from backend.src.models.log import setup_logging
    from backend.src.db.migrate import run_migrations

    setup_logging()
    run_migrations()
    logger.info("Starting supplement data sync...")
    sync_valuation()
    sync_news()
    logger.info("Done.")


if __name__ == "__main__":
    main()
