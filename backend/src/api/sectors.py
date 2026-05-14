"""Sector analysis API routes."""
import logging
import threading
from urllib.parse import unquote

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Background refresh state ---
_refresh_status = {"running": False, "message": "", "last_updated": None}


def _run_sector_refresh():
    """Background thread target for sector data computation."""
    global _refresh_status
    if _refresh_status["running"]:
        return

    _refresh_status["running"] = True
    _refresh_status["message"] = "正在计算板块数据..."

    try:
        from backend.src.services.sector_service import compute_all_sectors
        snap_date = compute_all_sectors()
        _refresh_status["message"] = f"板块数据更新完成（{snap_date}）"
        _refresh_status["last_updated"] = snap_date
    except Exception as e:
        logger.error(f"Sector refresh failed: {e}")
        _refresh_status["message"] = f"更新失败: {e}"
    finally:
        _refresh_status["running"] = False


# --- Page Routes ---

@router.get("/sector-analysis", response_class=HTMLResponse)
async def sector_analysis_page(request: Request):
    from backend.src.models.sector import SectorSnapshot
    last_updated = SectorSnapshot.last_update()
    return templates.TemplateResponse(request, "pages/sector_analysis.html", {
        "last_updated": last_updated,
    })


@router.get("/sector-analysis/{sector_name:path}", response_class=HTMLResponse)
async def sector_detail_page(request: Request, sector_name: str):
    """Sector detail page with trend chart + constituent stocks."""
    from backend.src.models.sector import SectorSnapshot
    sector_name = unquote(sector_name)
    snap = SectorSnapshot.get(sector_name)
    return templates.TemplateResponse(request, "pages/sector_detail.html", {
        "sector_name": sector_name,
        "snap": snap,
    })


# --- API Routes ---

@router.get("/api/sectors/list")
async def sector_list(request: Request,
                      sort_by: str = Query("heat_rank"),
                      sort_order: str = Query("asc"),
                      levels: str = Query("")):
    """Return sector overview table HTML fragment (HTMX-compatible)."""
    from backend.src.services.data_service import get_sector_list
    level_list = [l.strip() for l in levels.split(",") if l.strip()] if levels else None
    sectors = get_sector_list(sort_by=sort_by, sort_order=sort_order, levels=level_list)
    return templates.TemplateResponse(request, "components/sector_table.html", {
        "sectors": sectors,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "levels": levels,
    })


@router.get("/api/sectors/rotation")
async def sector_rotation(request: Request,
                          time_range: str = Query("1y"),
                          granularity: str = Query("monthly"),
                          levels: str = Query("")):
    """Return sector rotation data as JSON, including unrotated sectors."""
    from backend.src.services.sector_service import get_rotation_data
    from backend.src.models.sector import SectorSnapshot
    level_list = [l.strip() for l in levels.split(",") if l.strip()] if levels else None
    data = get_rotation_data(time_range=time_range, granularity=granularity,
                             levels=level_list)

    # Find sectors with zero movement count (never rotated), respecting level filter
    all_sectors = SectorSnapshot.all_ordered(sort_by="sector_name", sort_order="asc",
                                             levels=level_list)
    rotated_names = set()
    for leader in data.get("leaders", []):
        for t in leader.get("top3", []):
            rotated_names.add(t["sector"])
    unrotated = [s for s in all_sectors if s["sector_name"] not in rotated_names and s.get("trend_available")]
    data["unrotated"] = unrotated
    return JSONResponse(data)


@router.get("/api/sectors/{sector_name:path}/trend")
async def sector_trend(request: Request, sector_name: str,
                       period: str = Query("daily"),
                       time_range: str = Query("1y")):
    """Return sector trend K-line data as JSON (ECharts format)."""
    from backend.src.services.sector_service import get_sector_trend
    sector_name = unquote(sector_name)
    data = get_sector_trend(sector_name, period=period, time_range=time_range)
    return JSONResponse(data)


@router.get("/api/sectors/{sector_name:path}/constituents")
async def sector_constituents(request: Request, sector_name: str):
    """Return sector constituent stocks HTML fragment."""
    from backend.src.services.sector_service import get_sector_constituents
    sector_name = unquote(sector_name)
    stocks = get_sector_constituents(sector_name)
    return templates.TemplateResponse(request, "components/sector_constituents.html", {
        "sector_name": sector_name,
        "stocks": stocks,
    })


@router.post("/api/sectors/refresh")
async def trigger_sector_refresh(request: Request):
    """Manually trigger sector analysis data refresh."""
    if not _refresh_status["running"]:
        thread = threading.Thread(target=_run_sector_refresh, daemon=True)
        thread.start()
        _refresh_status["message"] = "正在计算板块数据..."
    return templates.TemplateResponse(request, "components/sector_update_status.html", {
        "s": _refresh_status,
    })


@router.get("/api/sectors/refresh/status")
async def sector_refresh_status(request: Request):
    """Poll sector refresh progress."""
    response = templates.TemplateResponse(request, "components/sector_update_status.html", {
        "s": _refresh_status,
    })
    if not _refresh_status["running"] and _refresh_status["last_updated"]:
        response.headers["HX-Trigger"] = "sector-update-done"
    return response
