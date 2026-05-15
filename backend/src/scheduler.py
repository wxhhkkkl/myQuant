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
    # Only scan models with is_running=1
    running = StrategyConfig.get_running_models()
    for config in running:
        model_name = config["model_name"]
        stock_list = config.get("stock_list")
        if not stock_list:
            continue

        import json
        stock_list = json.loads(stock_list) if isinstance(stock_list, str) else stock_list
        params = config.get("params", {})
        if isinstance(params, str):
            params = json.loads(params)
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
