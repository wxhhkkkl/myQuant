import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.src.config import BASE_DIR
from backend.src.templates import templates
from backend.src.db.migrate import run_migrations
from backend.src.db.duckdb_schema import init_schema
from backend.src.models.log import setup_logging
from backend.src.scheduler import start_scheduler, stop_scheduler
from backend.src.api.errors import not_found_handler, server_error_handler

logger = logging.getLogger(__name__)


def _seed_models():
    """Register built-in quant models on first startup."""
    from backend.src.models.quant_model import QuantModel
    QuantModel.create_table()
    QuantModel.register_defaults()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting myQuant...")
    run_migrations()
    init_schema()
    _seed_models()
    _connect_qmt()
    start_scheduler()
    yield
    stop_scheduler()
    _disconnect_qmt()
    logger.info("myQuant stopped.")


def _connect_qmt():
    try:
        from backend.src.services.qmt_connector import get_connector
        conn = get_connector()
        if conn.connect():
            logger.info("QMT connected")
        else:
            logger.warning("QMT not available — trading features disabled")
    except Exception:
        logger.warning("QMT connection failed", exc_info=True)


def _disconnect_qmt():
    try:
        from backend.src.services.qmt_connector import get_connector
        get_connector().disconnect()
    except Exception:
        pass


app = FastAPI(title="myQuant", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(500, server_error_handler)

static_dir = BASE_DIR.parent.parent / "frontend" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

from backend.src.api.stocks import router as stocks_router
from backend.src.api.watchlist import router as watchlist_router
from backend.src.api.models import router as models_router
from backend.src.api.backtest import router as backtest_router
from backend.src.api.trading import router as trading_router
from backend.src.api.account import router as account_router
from backend.src.api.data import router as data_router
from backend.src.api.sectors import router as sectors_router

app.include_router(stocks_router)
app.include_router(watchlist_router)
app.include_router(models_router)
app.include_router(backtest_router)
app.include_router(trading_router)
app.include_router(account_router)
app.include_router(data_router)
app.include_router(sectors_router)


@app.get("/")
async def index():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/stocks")
