"""Unit tests for MA cross model: SMA calculation, crossover detection, performance stats."""
import pytest
from backend.src.services.model_service import calc_ma, detect_crossover


class TestCalcMA:
    def test_basic_sma_5(self):
        values = [10, 11, 12, 13, 14, 15, 16]
        result = calc_ma(values, 5)
        assert result[4] == pytest.approx(12.0)  # avg of 10-14
        assert result[5] == pytest.approx(13.0)  # avg of 11-15
        assert result[6] == pytest.approx(14.0)  # avg of 12-16

    def test_early_positions_are_none(self):
        values = [10, 11, 12, 13, 14]
        result = calc_ma(values, 5)
        assert result[0] is None
        assert result[1] is None
        assert result[2] is None
        assert result[3] is None
        assert result[4] == pytest.approx(12.0)

    def test_window_equals_length(self):
        values = [10, 20, 30]
        result = calc_ma(values, 3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(20.0)

    def test_window_larger_than_data(self):
        values = [10, 20]
        result = calc_ma(values, 5)
        assert all(v is None for v in result)

    def test_constant_values(self):
        values = [5.0] * 10
        result = calc_ma(values, 3)
        for i in range(2, 10):
            assert result[i] == pytest.approx(5.0)

    def test_empty_list(self):
        assert calc_ma([], 5) == []


class TestDetectCrossover:
    def test_golden_cross(self):
        closes = [10, 10, 10, 10, 10]
        ma_short = [None, None, None, 5, 15]
        ma_long = [None, None, None, 10, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "BUY"
        assert signals[0]["index"] == 4

    def test_death_cross(self):
        closes = [10, 10, 10, 10, 10]
        ma_short = [None, None, None, 15, 5]
        ma_long = [None, None, None, 10, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "SELL"
        assert signals[0]["index"] == 4

    def test_no_cross_when_short_always_above(self):
        closes = [10] * 10
        ma_short = [None, None, None, None, None, 20, 21, 22, 23, 24]
        ma_long = [None, None, None, None, None, 10, 10, 10, 10, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 0

    def test_no_cross_when_short_always_below(self):
        closes = [10] * 10
        ma_short = [None, None, None, None, None, 5, 6, 7, 8, 9]
        ma_long = [None, None, None, None, None, 10, 10, 10, 10, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 0

    def test_ignores_none_positions(self):
        closes = [10, 10, 10, 10, 10, 10]
        ma_short = [None, None, 10, 15, 10, 15]
        ma_long = [None, None, 10, 10, 15, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 3
        assert signals[0]["signal_type"] == "BUY"
        assert signals[1]["signal_type"] == "SELL"
        assert signals[2]["signal_type"] == "BUY"

    def test_multiple_signals(self):
        closes = [10] * 10
        ma_short = [None, None, None, None, 15, 5, 15, 5, 15, 5]
        ma_long = [None, None, None, None, 10, 10, 10, 10, 10, 10]
        signals = detect_crossover(closes, ma_short, ma_long)
        assert len(signals) == 5


class TestComputePerformance:
    def test_basic_stats(self):
        from backend.src.services.model_service import compute_performance
        signals = [
            {"trade_date": "2025-01-10", "signal_type": "BUY", "signal_price": 10.0},
            {"trade_date": "2025-02-10", "signal_type": "SELL", "signal_price": 12.0},
            {"trade_date": "2025-03-10", "signal_type": "BUY", "signal_price": 13.0},
            {"trade_date": "2025-04-10", "signal_type": "SELL", "signal_price": 10.0},
        ]
        result = compute_performance(signals)
        assert result["total_signals"] == 4
        assert result["trade_pairs"] == 2
        assert result["cumulative_return"] == pytest.approx(-3.08, abs=0.1)  # +20% 1st, -23.08% 2nd
        assert result["win_rate"] == pytest.approx(50.0)

    def test_empty_signals(self):
        from backend.src.services.model_service import compute_performance
        result = compute_performance([])
        assert result["total_signals"] == 0
        assert result["trade_pairs"] == 0
        assert result["cumulative_return"] == 0.0
        assert result["win_rate"] == 0.0

    def test_only_buy_no_sell(self):
        from backend.src.services.model_service import compute_performance
        signals = [
            {"trade_date": "2025-01-10", "signal_type": "BUY", "signal_price": 10.0},
            {"trade_date": "2025-02-10", "signal_type": "BUY", "signal_price": 12.0},
        ]
        result = compute_performance(signals)
        assert result["total_signals"] == 2
        assert result["trade_pairs"] == 0
        assert result["cumulative_return"] == 0.0
        assert result["win_rate"] == 0.0

    def test_all_wins(self):
        from backend.src.services.model_service import compute_performance
        signals = [
            {"trade_date": "2025-01-10", "signal_type": "BUY", "signal_price": 10.0},
            {"trade_date": "2025-02-10", "signal_type": "SELL", "signal_price": 15.0},
        ]
        result = compute_performance(signals)
        assert result["trade_pairs"] == 1
        assert result["win_rate"] == pytest.approx(100.0)
        assert result["cumulative_return"] == pytest.approx(50.0)
