import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.models.position import Position
from backend.src.models.account_snapshot import AccountSnapshot
from backend.src.services.account_service import (
    aggregate_overview, build_asset_curve, sync_positions_from_qmt,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    return templates.TemplateResponse(request, "pages/account.html", {})


@router.get("/api/account/overview", response_class=HTMLResponse)
async def account_overview(request: Request):
    from datetime import datetime
    from backend.src.services.qmt_connector import get_connector

    connector = get_connector()
    available_cash = 0.0

    # Sync positions and cash from QMT if connected
    if connector.is_connected():
        try:
            sync_positions_from_qmt(connector)
            asset = connector.query_asset()
            if asset:
                available_cash = asset.cash or 0.0
        except Exception:
            logger.warning("Failed to query QMT", exc_info=True)

    positions = Position.all()
    overview = aggregate_overview(positions, available_cash=available_cash)
    snapshots = AccountSnapshot.recent(limit=1)
    last_updated = snapshots[0]["created_at"] if snapshots else datetime.now().isoformat()
    return templates.TemplateResponse(request, "components/account_overview.html", {
        "overview": overview,
        "last_updated": last_updated,
    })


@router.get("/api/account/positions", response_class=HTMLResponse)
async def account_positions(request: Request):
    positions = Position.all()
    return templates.TemplateResponse(request, "components/positions.html", {
        "positions": positions,
    })


@router.get("/api/account/curve")
async def account_curve():
    snapshots = AccountSnapshot.recent(limit=90)
    curve = build_asset_curve(list(reversed(snapshots)))
    return curve
