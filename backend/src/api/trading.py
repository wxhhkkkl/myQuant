import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.models.trade_signal import TradeSignal
from backend.src.models.order import Order
from backend.src.models.quant_model import QuantModel
from backend.src.models.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Page ────────────────────────────────────────────────────────────────────

@router.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading page: model list, signal scan, order management."""
    return templates.TemplateResponse(request, "pages/trading.html", {})


# ── Model instance management (US1) ─────────────────────────────────────────

@router.get("/api/trading/models")
async def list_trading_models():
    """Return all active models with run state and config."""
    models = QuantModel.all_active()
    result = []
    for m in models:
        import json as _json
        if m.get("default_params"):
            try:
                m["default_params"] = _json.loads(m["default_params"])
            except (_json.JSONDecodeError, TypeError):
                pass
        config = StrategyConfig.get(m["model_name"])
        if config and config.get("params"):
            try:
                config["params"] = _json.loads(config["params"])
            except (_json.JSONDecodeError, TypeError):
                pass
        result.append({
            "model_name": m["model_name"],
            "display_name": m["display_name"],
            "description": m.get("description", ""),
            "default_params": m.get("default_params", {}),
            "is_running": bool(config["is_running"]) if config else False,
            "capital": config["capital"] if config else 100000,
            "config": {
                "id": config["id"],
                "params": config.get("params", {}),
                "position_pct": config.get("position_pct", 100),
                "time_range": config.get("time_range", "1y"),
            } if config else None,
        })
    return result


@router.post("/api/trading/models/{model_name}/start")
async def start_model(model_name: str, request: Request):
    model = QuantModel.get(model_name)
    if not model:
        return JSONResponse({"error": "模型不存在"}, status_code=404)
    data = await request.json()
    params = data.get("params", {})
    position_pct = data.get("position_pct", 100)
    time_range = data.get("time_range", "1y")
    stock_list = data.get("stock_list")

    short = params.get("short", 5)
    long = params.get("long", 20)
    if short >= long:
        return JSONResponse({"error": "快线周期必须小于慢线周期"}, status_code=400)

    StrategyConfig.upsert(
        model_name=model_name,
        params=params,
        position_pct=position_pct,
        time_range=time_range,
        stock_list=stock_list,
    )
    StrategyConfig.set_running(model_name, True)
    return {"status": "running", "model_name": model_name}


@router.post("/api/trading/models/{model_name}/stop")
async def stop_model(model_name: str):
    model = QuantModel.get(model_name)
    if not model:
        return JSONResponse({"error": "模型不存在"}, status_code=404)
    StrategyConfig.set_running(model_name, False)
    return {"status": "stopped", "model_name": model_name}


@router.put("/api/trading/models/{model_name}/config")
async def update_model_config(model_name: str, request: Request):
    model = QuantModel.get(model_name)
    if not model:
        return JSONResponse({"error": "模型不存在"}, status_code=404)
    data = await request.json()
    params = data.get("params", {})
    position_pct = data.get("position_pct", 100)
    time_range = data.get("time_range", "1y")

    short = params.get("short", 5)
    long = params.get("long", 20)
    if short >= long:
        return JSONResponse({"error": "快线周期必须小于慢线周期"}, status_code=400)
    if position_pct < 1 or position_pct > 100:
        return JSONResponse({"error": "仓位比例需在 1%~100% 之间"}, status_code=400)
    if time_range not in ("1m", "3m", "6m", "1y"):
        return JSONResponse({"error": "无效的时间范围"}, status_code=400)

    StrategyConfig.upsert(
        model_name=model_name,
        params=params,
        position_pct=position_pct,
        time_range=time_range,
    )
    return {"status": "ok", "model_name": model_name}


@router.get("/api/signals", response_class=HTMLResponse)
async def list_signals(request: Request):
    """Return signals list as HTML component."""
    signals = TradeSignal.all()
    return templates.TemplateResponse(request, "components/signals.html", {
        "signals": signals,
    })


@router.post("/api/signals/{signal_id}/confirm")
async def confirm_signal(signal_id: int, request: Request = None):
    sig = TradeSignal.get(signal_id)
    if sig is None:
        return JSONResponse({"error": "Signal not found"}, status_code=404)

    quantity = None
    price = None
    if request:
        try:
            data = await request.json()
            quantity = data.get("quantity")
            price = data.get("price")
        except Exception:
            pass

    from backend.src.services.trade_service import confirm_signal as do_confirm
    result = do_confirm(signal_id, quantity, price)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@router.post("/api/signals/{signal_id}/ignore")
async def ignore_signal_endpoint(signal_id: int):
    sig = TradeSignal.get(signal_id)
    if sig is None:
        return JSONResponse({"error": "Signal not found"}, status_code=404)
    TradeSignal.update_status(signal_id, "ignored")
    return {"status": "ignored", "signal_id": signal_id}


# ── Signal Scanning (US2) ────────────────────────────────────────────────

@router.get("/api/trading/position")
async def get_position(stock_code: str, model_name: str = "ma_cross"):
    from backend.src.models.position import Position
    pos = Position.get(stock_code, model_name)
    if not pos:
        return {"stock_code": stock_code, "quantity": 0, "avg_cost": 0, "market_value": 0}
    return {
        "stock_code": stock_code,
        "model_name": model_name,
        "quantity": pos.get("quantity", 0),
        "avg_cost": pos.get("avg_cost", 0),
        "current_price": pos.get("current_price", 0),
        "market_value": pos.get("market_value", 0),
        "profit_loss": pos.get("profit_loss", 0),
        "profit_loss_pct": pos.get("profit_loss_pct", 0),
    }


@router.post("/api/trading/models/{model_name}/scan")
async def scan_signals_endpoint(model_name: str, request: Request):
    from backend.src.services.trade_service import scan_signals

    data = await request.json()
    signal_type = data.get("signal_type", "BUY")
    scope = data.get("scope", "watchlist")
    industry = data.get("industry")
    exclude_st = data.get("exclude_st", False)
    exclude_loss = data.get("exclude_loss", False)

    if signal_type not in ("BUY", "SELL"):
        return JSONResponse({"error": "signal_type must be BUY or SELL"}, status_code=400)

    results = scan_signals(model_name, signal_type, scope, industry, exclude_st, exclude_loss)

    is_hx = "hx-request" in request.headers.get("hx-request", "").lower() or \
            request.headers.get("HX-Request") == "true"
    if is_hx:
        return templates.TemplateResponse(request, "components/scan_results.html", {
            "results": results,
            "model_name": model_name,
            "signal_type": signal_type,
        })
    return {"model_name": model_name, "signal_type": signal_type, "results": results, "count": len(results)}


# ── Order monitoring (US4) ────────────────────────────────────────────────

@router.get("/api/trading/orders/monitor", response_class=HTMLResponse)
async def monitor_orders(request: Request):
    from backend.src.services.trade_service import monitor_orders as do_monitor
    orders = do_monitor()
    return templates.TemplateResponse(request, "components/orders.html", {
        "orders": orders,
    })


@router.post("/api/trading/orders/{order_id}/retry")
async def retry_order(order_id: int):
    from backend.src.services.trade_service import retry_order as do_retry
    result = do_retry(order_id)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return result


@router.get("/api/trading/models/{model_name}/orders", response_class=HTMLResponse)
async def model_orders(request: Request, model_name: str):
    orders = Order.all(model_name)
    return templates.TemplateResponse(request, "components/orders.html", {
        "orders": orders,
        "model_name": model_name,
    })


# ── Performance (US5) ─────────────────────────────────────────────────────

@router.get("/api/trading/models/{model_name}/performance")
async def model_performance(model_name: str, request: Request):
    from backend.src.services.trade_service import get_model_performance
    perf = get_model_performance(model_name)

    is_hx = "hx-request" in request.headers.get("hx-request", "").lower() or \
            request.headers.get("HX-Request") == "true"
    if is_hx:
        return templates.TemplateResponse(request, "components/model_performance.html", perf)
    return perf


@router.get("/api/orders", response_class=HTMLResponse)
async def list_orders(request: Request):
    """Return orders list as HTML component."""
    orders = Order.all()
    return templates.TemplateResponse(request, "components/orders.html", {
        "orders": orders,
    })


@router.post("/api/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=422)

    stock_code = data.get("stock_code")
    order_type = data.get("order_type")
    price = data.get("price")
    quantity = data.get("quantity")
    signal_id = data.get("signal_id")

    if not all([stock_code, order_type, price, quantity]):
        return JSONResponse({"error": "stock_code, order_type, price, quantity required"}, status_code=422)

    try:
        order_id = Order.create(
            stock_code=stock_code,
            order_type=order_type,
            price=float(price),
            quantity=int(quantity),
            signal_id=signal_id,
        )
    except Exception:
        return JSONResponse({"error": "Failed to create order"}, status_code=422)

    return {"id": order_id, "status": "submitted"}


@router.delete("/api/orders/{order_id}")
async def cancel_order(order_id: int):
    order = Order.get(order_id)
    if order is None:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    Order.cancel(order_id)
    return {"status": "cancelled", "order_id": order_id}
