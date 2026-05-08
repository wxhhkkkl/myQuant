import pytest


class TestSignalGeneration:
    """Unit tests for trade signal generation and confirmation."""

    def test_generate_signal_creates_db_row(self):
        """generate_signal() should insert into trade_signals table."""
        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        sig_id = TradeSignal.create(
            stock_code="000001.SZ",
            model_name="ma_cross",
            signal_type="BUY",
            signal_price=12.5,
            signal_reason="MA5 crossed above MA20",
        )

        assert sig_id is not None
        assert sig_id > 0

    def test_confirm_signal_updates_status(self):
        """confirm() should set is_confirmed = 1."""
        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        sig_id = TradeSignal.create(
            stock_code="000001.SZ", model_name="ma_cross",
            signal_type="BUY", signal_price=10.0,
            signal_reason="Golden cross",
        )
        TradeSignal.confirm(sig_id)
        sig = TradeSignal.get(sig_id)

        assert sig is not None
        assert sig["is_confirmed"] == 1

    def test_dismiss_signal_removes_it(self):
        """dismiss() should delete the signal."""
        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        sig_id = TradeSignal.create(
            stock_code="000001.SZ", model_name="ma_cross",
            signal_type="SELL", signal_price=10.0,
            signal_reason="Death cross",
        )
        TradeSignal.dismiss(sig_id)
        sig = TradeSignal.get(sig_id)

        assert sig is None

    def test_pending_signals_returns_unconfirmed(self):
        """pending() should return only unconfirmed signals."""
        from backend.src.models.trade_signal import TradeSignal

        TradeSignal.create_table()
        # Clear any existing signals
        TradeSignal.create_table()  # Re-create

        id1 = TradeSignal.create("000001.SZ", "ma_cross", "BUY", 10.0, "test1")
        id2 = TradeSignal.create("000002.SZ", "ma_cross", "SELL", 20.0, "test2")
        TradeSignal.confirm(id2)

        pending = TradeSignal.pending()

        assert isinstance(pending, list)
        # Only id1 should be pending
        pending_ids = [s["id"] for s in pending]
        assert id1 in pending_ids
        assert id2 not in pending_ids
