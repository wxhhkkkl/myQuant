import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _daily_sync_job():
    from backend.src.scripts.daily_sync import run_daily_sync
    run_daily_sync()


def _signal_scan_job():
    from backend.src.services.trade_service import TradeService
    from backend.src.services.model_service import MaCrossModel
    from backend.src.models.strategy_config import StrategyConfig

    svc = TradeService()
    config = StrategyConfig.get("ma_cross")
    if not config or not config.get("stock_list"):
        return

    import json
    stock_list = json.loads(config["stock_list"]) if isinstance(config["stock_list"], str) else config["stock_list"]
    params = json.loads(config["params"]) if isinstance(config["params"], str) else config["params"]
    model = MaCrossModel(short=params.get("short", 5), long=params.get("long", 20))
    svc.scan_and_signal(model, stock_list)


def start_scheduler():
    logger.info("Starting scheduler...")
    # Daily sync at 18:00 (after market close)
    scheduler.add_job(_daily_sync_job, "cron", hour=18, minute=7, id="daily_sync")
    # Signal scan at 15:30 (after market close)
    scheduler.add_job(_signal_scan_job, "cron", hour=15, minute=37, id="signal_scan")
    scheduler.start()
    logger.info("Scheduler started.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
