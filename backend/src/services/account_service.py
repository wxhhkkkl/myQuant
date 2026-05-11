import logging

logger = logging.getLogger(__name__)


def calc_position_pnl(avg_cost: float, current_price: float,
                      quantity: int) -> tuple[float, float]:
    """Calculate position profit/loss and percentage."""
    if quantity == 0 or avg_cost == 0:
        return 0.0, 0.0
    pnl = quantity * (current_price - avg_cost)
    pnl_pct = (current_price - avg_cost) / avg_cost * 100
    return pnl, pnl_pct


def aggregate_overview(positions: list, available_cash: float = 0.0) -> dict:
    """Aggregate account overview from positions and available cash."""
    total_market_value = sum(p.get("market_value", 0) for p in positions)
    total_pnl = sum(p.get("profit_loss", 0) for p in positions)
    return {
        "available_cash": available_cash,
        "market_value": total_market_value,
        "total_asset": available_cash + total_market_value,
        "total_pnl": total_pnl,
        "position_count": len(positions),
    }


def build_asset_curve(snapshots: list) -> list:
    """Build asset curve data from snapshot records."""
    return [
        {"date": s["snapshot_date"], "value": s["total_asset"]}
        for s in snapshots
    ]


def sync_positions_from_qmt(connector) -> list:
    """Sync positions from QMT. Returns list of position dicts."""
    from backend.src.models.position import Position

    Position.create_table()
    if not connector.is_connected():
        logger.warning("QMT not connected; cannot sync positions.")
        return []

    try:
        qmt_positions = connector.query_positions()
        for pos in qmt_positions:
            pnl, pnl_pct = calc_position_pnl(
                avg_cost=pos.avg_cost or 0,
                current_price=pos.current_price or 0,
                quantity=pos.quantity or 0,
            )
            Position.upsert(
                stock_code=pos.stock_code,
                stock_name=getattr(pos, "stock_name", "") or "",
                quantity=pos.quantity or 0,
                avg_cost=pos.avg_cost or 0,
                current_price=pos.current_price or 0,
            )
        return Position.all()
    except Exception:
        logger.exception("Failed to sync positions from QMT")
        return []
