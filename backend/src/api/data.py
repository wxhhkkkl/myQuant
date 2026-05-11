"""API endpoints for data management: batch update stock info."""
import threading
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from backend.src.services.data_service import run_stock_update, get_update_status
from backend.src.templates import templates

router = APIRouter()


@router.post("/api/data/update-stocks")
async def trigger_update_stocks(request: Request):
    status = get_update_status()
    if status["running"]:
        return templates.TemplateResponse(request, "components/update_status.html", {"s": status})

    thread = threading.Thread(target=run_stock_update, daemon=True)
    thread.start()
    # Return status with HTMX trigger to start polling
    from fastapi.responses import HTMLResponse
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
