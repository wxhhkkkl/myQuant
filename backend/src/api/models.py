import json
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.models.quant_model import QuantModel
from backend.src.models.strategy_config import StrategyConfig
from backend.src.models.trade_signal import TradeSignal

router = APIRouter()


@router.get("/models", response_class=HTMLResponse)
async def models_page(request: Request):
    models = QuantModel.all_active()
    for m in models:
        if m.get("default_params"):
            try:
                m["default_params"] = json.loads(m["default_params"])
            except (json.JSONDecodeError, TypeError):
                pass
    return templates.TemplateResponse(request, "pages/models.html", {"models": models})


@router.get("/models/{model_name}", response_class=HTMLResponse)
async def model_detail_page(request: Request, model_name: str):
    model = QuantModel.get(model_name)
    if not model:
        return HTMLResponse("模型不存在", status_code=404)
    if model.get("default_params"):
        try:
            model["default_params"] = json.loads(model["default_params"])
        except (json.JSONDecodeError, TypeError):
            pass
    config = StrategyConfig.get(model_name)
    if config and config.get("params"):
        try:
            config["params"] = json.loads(config["params"])
        except (json.JSONDecodeError, TypeError):
            pass
    return templates.TemplateResponse(request, "pages/model_detail.html", {
        "model": model,
        "config": config,
    })


@router.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    return templates.TemplateResponse(request, "pages/backtest.html")


# --- API Routes ---

@router.get("/api/models")
async def list_models():
    models = QuantModel.all_active()
    for m in models:
        if m.get("default_params"):
            try:
                m["default_params"] = json.loads(m["default_params"])
            except (json.JSONDecodeError, TypeError):
                pass
    return models


@router.get("/api/models/{name}/detail")
async def model_detail(name: str):
    model = QuantModel.get(name)
    if not model:
        return JSONResponse({"error": "模型不存在"}, status_code=404)
    if model.get("default_params"):
        try:
            model["default_params"] = json.loads(model["default_params"])
        except (json.JSONDecodeError, TypeError):
            pass
    config = StrategyConfig.get(name)
    if config and config.get("params"):
        try:
            config["params"] = json.loads(config["params"])
        except (json.JSONDecodeError, TypeError):
            pass
    return {"model": model, "config": config}


@router.put("/api/models/{name}/config")
async def save_model_config(name: str, request: Request):
    data = await request.json()
    stock_code = data.get("stock_code", "")
    params = data.get("params", {})
    position_pct = data.get("position_pct", 100)
    time_range = data.get("time_range", "1y")

    # Validate
    short = params.get("short", 5)
    long = params.get("long", 20)
    if short >= long:
        return JSONResponse({"error": "快线周期必须小于慢线周期"}, status_code=400)
    if position_pct < 1 or position_pct > 100:
        return JSONResponse({"error": "仓位比例需在 1%~100% 之间"}, status_code=400)
    if time_range not in ("1m", "3m", "6m", "1y"):
        return JSONResponse({"error": "无效的时间范围"}, status_code=400)

    StrategyConfig.upsert(
        model_name=name,
        params=params,
        stock_code=stock_code,
        position_pct=position_pct,
        time_range=time_range,
    )
    return {"status": "ok", "model_name": name}


@router.post("/api/models/{name}/signals")
async def generate_signals(name: str, request: Request):
    from backend.src.services.model_service import MaCrossModel

    data = await request.json()
    stock_code = data.get("stock_code", "")
    short = data.get("short", 5)
    long = data.get("long", 20)
    position_pct = data.get("position_pct", 100)
    time_range = data.get("time_range", "1y")

    # Validate
    if not stock_code:
        return JSONResponse({"error": "请选择标的"}, status_code=400)
    if short >= long:
        return JSONResponse({"error": "快线周期必须小于慢线周期"}, status_code=400)
    if position_pct < 1 or position_pct > 100:
        return JSONResponse({"error": "仓位比例需在 1%~100% 之间"}, status_code=400)
    if time_range not in ("1m", "3m", "6m", "1y"):
        return JSONResponse({"error": "无效的时间范围"}, status_code=400)

    try:
        model = MaCrossModel(short=short, long=long)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    result = model.scan_full_range(stock_code, time_range)
    if "error" in result:
        return JSONResponse(result, status_code=400)

    # Save config so backtest/trading can reference it
    StrategyConfig.upsert(
        model_name=name,
        params={"short": short, "long": long},
        stock_code=stock_code,
        position_pct=position_pct,
        time_range=time_range,
    )

    # Persist signals
    config = StrategyConfig.get(name)
    config_id = config["id"] if config else None
    for s in result["signals"]:
        TradeSignal.create(
            stock_code=stock_code,
            model_name=name,
            signal_type=s["signal_type"],
            signal_price=s["signal_price"],
            signal_reason=f"MA{short} {'上穿' if s['signal_type'] == 'BUY' else '下穿'}MA{long}",
            trade_date=s["trade_date"],
            config_id=config_id,
        )

    return result
