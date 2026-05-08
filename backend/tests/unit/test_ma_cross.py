import pytest


class TestMaCrossModel:
    """Unit tests for MA5/MA20 crossover signal logic."""

    @pytest.fixture
    def known_data(self):
        """Synthetic K-line data where we control the crossover."""
        # Prices steadily rising: MA5 will cross above MA20 at some point
        prices = [10.0] * 20  # Flat base for MA20 initialization
        prices += list(range(10, 30))  # Rising prices → MA5 crosses above MA20
        prices += list(range(30, 10, -1))  # Falling prices → MA5 crosses below MA20

        rows = []
        for i, price in enumerate(prices):
            rows.append({
                "trade_date": f"2025-{i + 1:02d}-01" if i < 30 else f"2025-{(i + 1) % 30:02d}-02",
                "close": price, "open": price - 0.1, "high": price + 0.1,
                "low": price - 0.2, "volume": 100000, "stock_code": "TEST.SZ",
            })
        return rows

    def test_calc_ma5_returns_correct_values(self, known_data):
        """MA5 should average the last 5 close prices."""
        from backend.src.services.model_service import calc_ma

        closes = [r["close"] for r in known_data]
        ma5 = calc_ma(closes, 5)

        assert len(ma5) == len(closes)
        # First 4 values should be None (not enough data)
        assert ma5[4] is not None
        # 5th value = average of first 5 closes
        expected = sum(closes[:5]) / 5
        assert abs(ma5[4] - expected) < 0.0001

    def test_calc_ma20_returns_correct_values(self, known_data):
        """MA20 should average the last 20 close prices."""
        from backend.src.services.model_service import calc_ma

        closes = [r["close"] for r in known_data]
        ma20 = calc_ma(closes, 20)

        assert len(ma20) == len(closes)
        assert ma20[19] is not None
        expected = sum(closes[:20]) / 20
        assert abs(ma20[19] - expected) < 0.0001

    def test_detect_golden_cross(self):
        """When MA5 crosses ABOVE MA20, signal should be BUY."""
        from backend.src.services.model_service import detect_crossover

        n = 30
        closes = [10.0] * n
        ma5 = [None] * 4 + [15.0] * 20 + [21.0] + [21.0] * 5
        ma20 = [None] * 19 + [17.0] * 11

        signals = detect_crossover(closes, ma5, ma20)
        buy_signals = [s for s in signals if s["signal_type"] == "BUY"]
        assert len(buy_signals) == 1, f"Expected 1 BUY, got {len(buy_signals)}: {signals}"

    def test_detect_death_cross(self):
        """When MA5 crosses BELOW MA20, signal should be SELL."""
        from backend.src.services.model_service import detect_crossover

        n = 30
        closes = [10.0] * n
        ma5 = [None] * 4 + [19.0] * 20 + [13.0] + [13.0] * 5
        ma20 = [None] * 19 + [15.0] * 11

        signals = detect_crossover(closes, ma5, ma20)
        sell_signals = [s for s in signals if s["signal_type"] == "SELL"]
        assert len(sell_signals) == 1, f"Expected 1 SELL, got {len(sell_signals)}: {signals}"

    def test_no_crossover_returns_empty(self):
        """When MAs never cross, no signals should be generated."""
        from backend.src.services.model_service import detect_crossover

        closes = [10.0] * 30
        ma5 = [None] * 4 + [10.0] * 26
        ma20 = [None] * 19 + [10.0] * 11

        signals = detect_crossover(closes, ma5, ma20)
        assert len(signals) == 0

    def test_ma_cross_model_with_params(self):
        """MaCrossModel should accept short/long window params."""
        from backend.src.services.model_service import MaCrossModel

        model = MaCrossModel(short=5, long=20)
        assert model.short == 5
        assert model.long == 20
        assert model.short < model.long
