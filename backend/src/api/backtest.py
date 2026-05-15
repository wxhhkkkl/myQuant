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


def _is_hx_request(request: Request) -> bool:
    return "hx-request" in request.headers.get("hx-request", "").lower() or \
           request.headers.get("HX-Request") == "true"


def _render_error(request: Request, error: str) -> HTMLResponse:
    return templates.TemplateResponse(request, "components/backtest_results.html",
                                      {"error": error})


def _get_stock_name(code: str) -> str:
    """Look up stock name from SQLite, return code if not found."""
    try:
        from backend.src.db.sqlite import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT stock_name FROM stocks WHERE stock_code = ?", (code,)
            ).fetchone()
            return row["stock_name"] if row else code
    except Exception:
        return code


@router.post("/api/backtest/run")
async def run_backtest_endpoint(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            if _is_hx_request(request):
                return _render_error(request, "Invalid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=422)
    else:
        form = await request.form()
        data = dict(form)

    model_name = data.get("model_name", "ma_cross")
    if "params" in data:
        params = data["params"]
    else:
        # Form data sends short/long as top-level fields
        params = {
            "short": int(data.get("short", 5)),
            "long": int(data.get("long", 20)),
        }
    stock_code = data.get("stock_code")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    initial_capital = data.get("initial_capital", 100000)

    if not stock_code or not start_date or not end_date:
        if _is_hx_request(request):
            return _render_error(request, "stock_code, start_date, end_date required")
        return JSONResponse({"error": "stock_code, start_date, end_date required"}, status_code=422)

    kline = get_kline(stock_code, start_date, end_date)
    if not kline:
        if _is_hx_request(request):
            return _render_error(request, "No K-line data for given period")
        return JSONResponse({"error": "No K-line data for given period"}, status_code=422)

    model = MaCrossModel(short=params.get("short", 5), long=params.get("long", 20))
    signals = model.generate_signals(kline)

    # Add trade_date from kline index to signals
    for s in signals:
        s["trade_date"] = kline[s["index"]]["trade_date"]

    result = run_backtest(stock_code, kline, signals,
                          initial_capital=float(initial_capital))

    if _is_hx_request(request):
        return templates.TemplateResponse(request, "components/backtest_results.html", result)
    return result


@router.post("/api/backtest/batch-run")
async def batch_run_backtest_endpoint(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
        except json.JSONDecodeError:
            if _is_hx_request(request):
                return _render_error(request, "Invalid JSON")
            return JSONResponse({"error": "Invalid JSON"}, status_code=422)
    else:
        form = await request.form()
        data = dict(form)

    model_name = data.get("model_name", "ma_cross")
    if "params" in data:
        params = data["params"]
    else:
        params = {
            "short": int(data.get("short", 5)),
            "long": int(data.get("long", 20)),
        }
    import json as _json
    model_params_str = _json.dumps(params)

    # stock_codes can be JSON list or comma-separated string (from form)
    stock_codes = data.get("stock_codes", [])
    if isinstance(stock_codes, str):
        stock_codes = [c.strip() for c in stock_codes.replace("，", ",").split(",") if c.strip()]

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    initial_capital = float(data.get("initial_capital", 100000))

    if not stock_codes or not start_date or not end_date:
        if _is_hx_request(request):
            return _render_error(request, "stock_codes, start_date, end_date required")
        return JSONResponse({"error": "stock_codes, start_date, end_date required"}, status_code=422)

    stock_codes = list(dict.fromkeys(stock_codes))

    results = []
    failed = []
    for code in stock_codes:
        try:
            kline = get_kline(code, start_date, end_date)
            if not kline:
                failed.append({"stock_code": code, "stock_name": _get_stock_name(code), "error": "无K线数据"})
                continue
            model = MaCrossModel(short=params["short"], long=params["long"])
            signals = model.generate_signals(kline)
            for s in signals:
                s["trade_date"] = kline[s["index"]]["trade_date"]
            result = run_backtest(code, kline, signals,
                                  initial_capital=initial_capital,
                                  model_name=model_name,
                                  model_params=model_params_str)
            result["stock_name"] = _get_stock_name(code)
            result["stock_code"] = code
            results.append(result)
        except Exception as e:
            logger.exception(f"Batch backtest failed for {code}")
            failed.append({"stock_code": code, "stock_name": _get_stock_name(code), "error": str(e)})

    results.sort(key=lambda r: r.get("total_return", -999), reverse=True)

    if _is_hx_request(request):
        return templates.TemplateResponse(request, "components/backtest_batch_results.html", {
            "results": results,
            "failed": failed,
            "start_date": start_date,
            "end_date": end_date,
            "model_name": model_name,
        })
    return {
        "results": results,
        "failed": failed,
        "start_date": start_date,
        "end_date": end_date,
    }


@router.get("/api/backtest/history")
async def backtest_history(request: Request):
    rows = db.query(
        "SELECT run_id, model_name, stock_code, start_date, end_date, "
        "initial_capital, total_return, trade_count, created_at "
        "FROM backtest_results ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    data = [dict(zip(
        ["run_id", "model_name", "stock_code", "start_date", "end_date",
         "initial_capital", "total_return", "trade_count", "created_at"], r
    )) for r in rows]
    if _is_hx_request(request):
        return templates.TemplateResponse(request, "components/backtest_history.html", {"rows": data})
    return data


@router.get("/api/backtest/{run_id}")
async def backtest_result(request: Request, run_id: str):
    row = db.query(
        "SELECT * FROM backtest_results WHERE run_id = ?", (run_id,)
    ).fetchone()
    if not row:
        return JSONResponse({"error": "Not found"}, status_code=404)
    data = dict(zip(
        ["run_id", "model_name", "model_params", "stock_code", "start_date",
         "end_date", "initial_capital", "final_capital", "total_return",
         "annual_return", "max_drawdown", "sharpe_ratio", "trade_count",
         "win_rate", "created_at"],
        row
    ))
    if _is_hx_request(request):
        return templates.TemplateResponse(request, "components/backtest_detail.html", data)
    return data


@router.get("/api/backtest/{run_id}/trades")
async def backtest_trades(request: Request, run_id: str):
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
    data = [dict(zip(["id", "run_id", "trade_date", "trade_type", "price",
                       "quantity", "profit"], r)) for r in rows]
    if _is_hx_request(request):
        return templates.TemplateResponse(request, "components/backtest_trades.html", {"trades": data})
    return data
