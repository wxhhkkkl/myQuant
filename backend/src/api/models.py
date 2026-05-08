import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.models.quant_model import QuantModel
from backend.src.models.strategy_config import StrategyConfig

router = APIRouter()


@router.get("/models", response_class=HTMLResponse)
async def models_page(request: Request):
    return templates.TemplateResponse(request, "pages/models.html")


@router.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    return templates.TemplateResponse(request, "pages/backtest.html")


@router.get("/api/models")
async def list_models():
    return QuantModel.all_active()


@router.put("/api/models/{name}/params")
async def update_model_params(name: str, request: Request):
    data = await request.json()
    params = data.get("params") if isinstance(data, dict) else json.loads(data).get("params")
    StrategyConfig.upsert(name, params)
    return {"status": "ok", "model_name": name, "params": params}
