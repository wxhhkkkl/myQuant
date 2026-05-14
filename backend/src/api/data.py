"""API endpoints for data management: batch update stock info and K-line data."""
import threading
from datetime import date, datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from backend.src.services.data_service import (
    run_stock_update, get_update_status,
    get_kline_date_range, get_kline_update_status, run_kline_update,
)
from backend.src.templates import templates

router = APIRouter()


@router.post("/api/data/update-stocks")
async def trigger_update_stocks(request: Request):
    status = get_update_status()
    if status["running"]:
        return templates.TemplateResponse(request, "components/update_status.html", {"s": status})

    thread = threading.Thread(target=run_stock_update, daemon=True)
    thread.start()
    resp = templates.TemplateResponse(request, "components/update_status.html", {"s": {"running": True, "total": 0, "success": 0, "fail": 0, "failed_codes": []}})
    resp.headers["HX-Trigger"] = "poll-update"
    return resp


@router.get("/api/data/update-stocks/status", response_class=HTMLResponse)
async def check_update_status(request: Request):
    status = get_update_status()
    resp = templates.TemplateResponse(request, "components/update_status.html", {"s": status})
    if not status["running"]:
        resp.headers["HX-Trigger"] = "update-done"
    return resp


@router.get("/api/data/kline-range", response_class=HTMLResponse)
async def kline_range(request: Request):
    range_info = get_kline_date_range()
    return templates.TemplateResponse(request, "components/kline_range.html", {"range": range_info})


@router.post("/api/data/update-kline", response_class=HTMLResponse)
async def trigger_update_kline(request: Request,
                                start_date: str = Form(default="2020-01-01"),
                                end_date: str = Form(default="")):
    if not end_date:
        end_date = date.today().isoformat()

    status = get_kline_update_status()
    if status["running"]:
        return templates.TemplateResponse(request, "components/kline_update_status.html", {"s": status})

    thread = threading.Thread(target=run_kline_update, args=(start_date, end_date), daemon=True)
    thread.start()

    resp = templates.TemplateResponse(request, "components/kline_update_status.html", {
        "s": {"running": True, "message": f"正在下载 {start_date} ~ {end_date} K线数据..."}
    })
    resp.headers["HX-Trigger"] = "poll-kline-update"
    return resp


@router.get("/api/data/update-kline/status", response_class=HTMLResponse)
async def check_kline_update_status(request: Request):
    status = get_kline_update_status()
    resp = templates.TemplateResponse(request, "components/kline_update_status.html", {"s": status})
    if not status["running"]:
        resp.headers["HX-Trigger"] = "update-done"
    return resp
