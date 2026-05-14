import logging

logger = logging.getLogger(__name__)


def run_migrations():
    """Initialize all SQLite tables in dependency order."""
    from backend.src.models.stock import Stock
    from backend.src.models.quant_model import QuantModel
    from backend.src.models.watchlist import Watchlist
    from backend.src.models.fundamental import StockFundamental
    from backend.src.models.financial_report import FinancialReport
    from backend.src.models.sentiment_news import SentimentNews, SentimentCache
    from backend.src.models.strategy_config import StrategyConfig
    from backend.src.models.trade_signal import TradeSignal
    from backend.src.models.order import Order
    from backend.src.models.position import Position
    from backend.src.models.account_snapshot import AccountSnapshot
    from backend.src.models.log import create_log_table

    logger.info("Running SQLite migrations...")
    Stock.create_table()
    QuantModel.create_table()
    Watchlist.create_table()
    StockFundamental.create_table()
    FinancialReport.create_table()
    SentimentNews.create_table()
    SentimentCache.create_table()
    StrategyConfig.create_table()
    TradeSignal.create_table()
    Order.create_table()
    Position.create_table()
    AccountSnapshot.create_table()
    create_log_table()
    logger.info("SQLite migrations complete.")
