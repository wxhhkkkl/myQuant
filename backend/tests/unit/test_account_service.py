import pytest


class TestAccountService:
    """Unit tests for account position tracking and P&L calculation."""

    def test_calc_position_pnl(self):
        """Calculate profit/loss for a single position."""
        from backend.src.services.account_service import calc_position_pnl

        pnl, pnl_pct = calc_position_pnl(
            avg_cost=10.0, current_price=12.5, quantity=100
        )
        assert pnl == 250.0
        assert pnl_pct == 25.0

    def test_calc_position_pnl_loss(self):
        """Calculate negative P&L when price below cost."""
        from backend.src.services.account_service import calc_position_pnl

        pnl, pnl_pct = calc_position_pnl(
            avg_cost=20.0, current_price=15.0, quantity=200
        )
        assert pnl == -1000.0
        assert pnl_pct == -25.0

    def test_calc_position_pnl_zero_quantity(self):
        """Zero quantity should produce zero P&L."""
        from backend.src.services.account_service import calc_position_pnl

        pnl, pnl_pct = calc_position_pnl(
            avg_cost=10.0, current_price=12.0, quantity=0
        )
        assert pnl == 0.0
        assert pnl_pct == 0.0

    def test_aggregate_account_overview(self):
        """Aggregate overview from positions and cash."""
        from backend.src.services.account_service import aggregate_overview

        positions = [
            {"market_value": 5000.0, "profit_loss": 200.0},
            {"market_value": 3000.0, "profit_loss": -100.0},
        ]
        overview = aggregate_overview(positions, available_cash=2000.0)

        assert overview["available_cash"] == 2000.0
        assert overview["market_value"] == 8000.0
        assert overview["total_asset"] == 10000.0
        assert overview["total_pnl"] == 100.0

    def test_aggregate_overview_empty_positions(self):
        """Overview with no positions should show only cash."""
        from backend.src.services.account_service import aggregate_overview

        overview = aggregate_overview([], available_cash=50000.0)
        assert overview["total_asset"] == 50000.0
        assert overview["market_value"] == 0.0
        assert overview["total_pnl"] == 0.0

    def test_asset_curve_from_snapshots(self):
        """Build asset curve from snapshot data."""
        from backend.src.services.account_service import build_asset_curve

        snapshots = [
            {"snapshot_date": "2025-01-01", "total_asset": 100000.0},
            {"snapshot_date": "2025-01-02", "total_asset": 101000.0},
            {"snapshot_date": "2025-01-03", "total_asset": 99500.0},
        ]
        curve = build_asset_curve(snapshots)

        assert len(curve) == 3
        assert curve[0]["date"] == "2025-01-01"
        assert curve[0]["value"] == 100000.0
        assert curve[2]["value"] == 99500.0

    def test_asset_curve_empty_returns_empty(self):
        """Empty snapshots should return empty list."""
        from backend.src.services.account_service import build_asset_curve

        curve = build_asset_curve([])
        assert curve == []
