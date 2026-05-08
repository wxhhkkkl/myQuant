import pytest


class TestBacktestEngine:
    """Unit tests for backtest engine accuracy."""

    def _make_kline(self, closes):
        """Convert a list of close prices to K-line rows."""
        rows = []
        for i, close in enumerate(closes):
            rows.append({
                "trade_date": f"2025-01-{i + 1:02d}",
                "open": close - 0.1, "high": close + 0.2,
                "low": close - 0.2, "close": close,
                "volume": 100000, "amount": int(close * 100000),
            })
        return rows

    def test_buy_and_sell_trades_are_recorded(self):
        """Backtest should record BUY and SELL trades when signals exist."""
        from backend.src.services.backtest_service import run_backtest

        closes = [10.0] * 20 + list(range(10, 15)) + list(range(15, 10, -1))
        kline = self._make_kline(closes)

        signals = [
            {"trade_date": "2025-01-25", "signal_type": "BUY"},
            {"trade_date": "2025-01-28", "signal_type": "SELL"},
        ]

        result = run_backtest("TEST.SZ", kline, signals, initial_capital=100000)

        assert result["trade_count"] >= 2
        assert "trades" in result
        assert len(result["trades"]) > 0

    def test_initial_capital_is_tracked(self):
        """Backtest should use the provided initial capital."""
        from backend.src.services.backtest_service import run_backtest

        kline = self._make_kline([10.0] * 30)
        signals = []

        result = run_backtest("TEST.SZ", kline, signals, initial_capital=50000)
        assert result["initial_capital"] == 50000

    def test_no_signals_means_no_trades(self):
        """With no signals, no trades should execute."""
        from backend.src.services.backtest_service import run_backtest

        kline = self._make_kline([10.0] * 30)
        result = run_backtest("TEST.SZ", kline, [], initial_capital=100000)

        assert result["trade_count"] == 0
        assert len(result["trades"]) == 0

    def test_total_return_without_trades_is_zero(self):
        """Without any trades, the total return should be 0."""
        from backend.src.services.backtest_service import run_backtest

        kline = self._make_kline([10.0] * 30)
        result = run_backtest("TEST.SZ", kline, [], initial_capital=100000)

        assert result["total_return"] == 0.0

    def test_max_drawdown_calculation(self):
        """Max drawdown should be non-positive and <= 0."""
        from backend.src.services.backtest_service import run_backtest

        closes = [10.0] * 10 + [8.0, 7.0, 9.0, 10.0]  # Drawdown then recovery
        kline = self._make_kline(closes)

        signals = [
            {"trade_date": "2025-01-11", "signal_type": "BUY"},
            {"trade_date": "2025-01-14", "signal_type": "SELL"},
        ]

        result = run_backtest("TEST.SZ", kline, signals, initial_capital=100000)
        assert result["max_drawdown"] <= 0

    def test_result_contains_all_required_fields(self):
        """Backtest result must include all required summary fields."""
        from backend.src.services.backtest_service import run_backtest

        kline = self._make_kline([10.0] * 30)
        result = run_backtest("TEST.SZ", kline, [], initial_capital=100000)

        required = ["total_return", "annual_return", "max_drawdown",
                     "sharpe_ratio", "trade_count", "win_rate", "trades"]
        for field in required:
            assert field in result, f"Missing field: {field}"
