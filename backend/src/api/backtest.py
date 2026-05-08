import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.db.duckdb import db
from backend.src.services.data_service import get_kline
from backend.src.services.model_service import MaCrossModel
from backend.src.services.backtest_service import run_backtest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/backtest/run")
async def run_backtest_endpoint(request: Request):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=422)

    model_name = data.get("model_name", "ma_cross")
    params = data.get("params", {"short": 5, "long": 20})
    stock_code = data.get("stock_code")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    initial_capital = data.get("initial_capital", 100000)

    if not stock_code or not start_date or not end_date:
        return JSONResponse({"error": "stock_code, start_date, end_date required"}, status_code=422)

    kline = get_kline(stock_code, start_date, end_date)
    if not kline:
        return JSONResponse({"error": "No K-line data for given period"}, status_code=422)

    model = MaCrossModel(short=params.get("short", 5), long=params.get("long", 20))
    signals = model.generate_signals(kline)

    # Add trade_date from kline index to signals
    for s in signals:
        s["trade_date"] = kline[s["index"]]["trade_date"]

    result = run_backtest(stock_code, kline, signals,
                          initial_capital=float(initial_capital))
    return result


@router.get("/api/backtest/history")
async def backtest_history():
    rows = db.query(
        "SELECT run_id, model_name, stock_code, start_date, end_date, "
        "initial_capital, total_return, trade_count, created_at "
        "FROM backtest_results ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    return [dict(zip(
        ["run_id", "model_name", "stock_code", "start_date", "end_date",
         "initial_capital", "total_return", "trade_count", "created_at"], r
    )) for r in rows]


@router.get("/api/backtest/{run_id}")
async def backtest_result(run_id: str):
    row = db.query(
        "SELECT * FROM backtest_results WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return dict(zip(
        ["run_id", "model_name", "model_params", "stock_code", "start_date",
         "end_date", "initial_capital", "final_capital", "total_return",
         "annual_return", "max_drawdown", "sharpe_ratio", "trade_count",
         "win_rate", "created_at"],
        row
    ))


@router.get("/api/backtest/{run_id}/trades")
async def backtest_trades(run_id: str):
    exists = db.query(
        "SELECT 1 FROM backtest_results WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not exists:
        return JSONResponse({"error": "Not found"}, status_code=404)

    rows = db.query(
        "SELECT id, run_id, trade_date, trade_type, price, quantity, profit "
        "FROM backtest_trades WHERE run_id = ? ORDER BY trade_date",
        (run_id,)
    ).fetchall()
    return [dict(zip(["id", "run_id", "trade_date", "trade_type", "price",
                       "quantity", "profit"], r)) for r in rows]
