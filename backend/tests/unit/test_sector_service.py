"""Unit tests for sector_service — TDD: these tests FAIL before implementation."""
import pytest


class TestDetectMovements:
    """T005: Sector movement detection — ≥10% gain over ≥5 consecutive trading days."""

    def test_detects_single_uptrend(self):
        """A clear 15% run over 8 days — first qualifying endpoint at 10%/5days."""
        from backend.src.services.sector_service import detect_movements

        # closes[0]=100 → closes[5]=110 (+10% at day 5, meeting min threshold)
        closes = [100, 102, 104, 103, 107, 110, 113, 115]
        result = detect_movements(closes)
        assert len(result) == 1
        assert result[0]["start_idx"] == 0
        assert result[0]["end_idx"] == 5
        assert result[0]["total_return"] == pytest.approx(10.0)

    def test_rejects_short_run(self):
        """A 12% gain over only 3 days should NOT be counted (<5 days)."""
        from backend.src.services.sector_service import detect_movements

        closes = [100, 107, 112]
        result = detect_movements(closes)
        assert len(result) == 0

    def test_rejects_small_gain(self):
        """An 8% gain over 10 days should NOT be counted (<10%)."""
        from backend.src.services.sector_service import detect_movements

        closes = [100, 101, 102, 101, 103, 102, 104, 105, 106, 107, 108]
        result = detect_movements(closes)
        assert len(result) == 0

    def test_detects_multiple_runs(self):
        """Two separate uptrends should be detected independently."""
        from backend.src.services.sector_service import detect_movements

        closes = [
            100, 105, 108, 110, 113, 115,  # +15% over 5 days
            112, 108, 106, 105, 103, 100,   # pullback
            100, 104, 107, 110, 113, 116,   # +16% over 5 days
        ]
        result = detect_movements(closes)
        assert len(result) == 2

    def test_handles_empty_data(self):
        """Empty close list should return empty movements."""
        from backend.src.services.sector_service import detect_movements

        result = detect_movements([])
        assert result == []

    def test_handles_insufficient_data(self):
        """Less than 5 data points should return empty."""
        from backend.src.services.sector_service import detect_movements

        result = detect_movements([100, 101, 102, 103])
        assert result == []

    def test_handles_flat_market(self):
        """Flat prices with <10% change should return empty."""
        from backend.src.services.sector_service import detect_movements

        closes = [100] * 20
        result = detect_movements(closes)
        assert len(result) == 0


class TestCalcValuationLevel:
    """T006: Valuation level calculation — tertile split."""

    def test_tertile_split_31_sectors(self):
        """With 31 sectors, should split roughly 10/10/11."""
        from backend.src.services.sector_service import calc_valuation_level

        # 31 ordered PE medians (low to high)
        all_pe = list(range(31))

        # Lowest PE → 低估
        assert calc_valuation_level(0, all_pe) == "低估"
        assert calc_valuation_level(9, all_pe) == "低估"

        # Middle PE → 适中
        assert calc_valuation_level(10, all_pe) == "适中"
        assert calc_valuation_level(20, all_pe) == "适中"

        # Highest PE → 高估
        assert calc_valuation_level(21, all_pe) == "高估"
        assert calc_valuation_level(30, all_pe) == "高估"

    def test_equal_pe_values(self):
        """All sectors with same PE should all be 适中."""
        from backend.src.services.sector_service import calc_valuation_level

        all_pe = [15.0] * 10
        assert calc_valuation_level(15.0, all_pe) == "适中"

    def test_small_sector_count(self):
        """With only 3 sectors, each gets a different level."""
        from backend.src.services.sector_service import calc_valuation_level

        all_pe = [10.0, 20.0, 30.0]
        assert calc_valuation_level(10.0, all_pe) == "低估"
        assert calc_valuation_level(20.0, all_pe) == "适中"
        assert calc_valuation_level(30.0, all_pe) == "高估"

    def test_handles_none_pe(self):
        """None PE should return '--'."""
        from backend.src.services.sector_service import calc_valuation_level

        all_pe = [10.0, 20.0, None, 30.0]
        result = calc_valuation_level(None, all_pe)
        assert result == "--"


class TestCalcHeatScore:
    """T004: Heat score formula — 0.4×ΔP + 0.3×ΔV + 0.3×up_ratio."""

    def test_heat_score_calculation(self):
        """Verify weighted formula produces correct score."""
        from backend.src.services.sector_service import calc_heat_score

        # 5% weekly gain, 10% volume increase, 60% stocks up
        score = calc_heat_score(5.0, 10.0, 0.6)
        expected = 5.0 * 0.4 + 10.0 * 0.3 + 0.6 * 0.3
        assert score == pytest.approx(expected)

    def test_heat_score_all_negative(self):
        """All inputs negative should produce negative score."""
        from backend.src.services.sector_service import calc_heat_score

        score = calc_heat_score(-10.0, -20.0, 0.0)
        assert score < 0

    def test_heat_score_all_positive(self):
        """All positive inputs should produce positive score."""
        from backend.src.services.sector_service import calc_heat_score

        score = calc_heat_score(10.0, 20.0, 1.0)
        assert score > 0

    def test_heat_score_with_none(self):
        """None inputs should default to 0."""
        from backend.src.services.sector_service import calc_heat_score

        score = calc_heat_score(None, None, None)
        assert score == 0.0
