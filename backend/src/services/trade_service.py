import logging
from datetime import datetime, time
from concurrent.futures import ThreadPoolExecutor

from backend.src.services.qmt_connector import get_connector, HAS_QMT

logger = logging.getLogger(__name__)

_TRADING_START = time(9, 30)
_TRADING_END = time(15, 0)


def _is_trading_time() -> bool:
    now = datetime.now().time()
    if datetime.now().weekday() >= 5:
        return False
    return _TRADING_START <= now <= _TRADING_END

_executor = ThreadPoolExecutor(max_workers=4)


class TradeService:
    """Trade execution service wrapping QMT xttrader."""

    def __init__(self):
        self._connector = get_connector()

    def _require_connection(self):
        if not self._connector.is_connected():
            raise RuntimeError("QMT not connected")

    def place_order(self, stock_code: str, order_type: str,
                    price: float, quantity: int, signal_id: int = None) -> dict:
        """Submit an order. Returns dict with order_id and status."""
        self._require_connection()
        qmt_order_id = self._connector.submit_order(stock_code, order_type, price, quantity)
        from backend.src.models.order import Order
        Order.create_table()
        db_id = Order.create(stock_code, order_type, price, quantity, signal_id)
        return {
            "order_id": qmt_order_id or db_id,
            "stock_code": stock_code,
            "order_type": order_type,
            "status": "submitted",
        }

    def scan_and_signal(self, model, stocks: list):
        """[DEPRECATED] Use scan_signals() instead. Kept for scheduler compat."""
        for stock_code in stocks:
            try:
                sigs = model.scan_stock(stock_code)
                if sigs:
                    for sig in sigs:
                        from backend.src.models.trade_signal import TradeSignal
                        TradeSignal.create(
                            stock_code=stock_code,
                            model_name=getattr(model, 'model_name', 'ma_cross'),
                            signal_type=sig["signal_type"],
                            signal_price=sig["price"],
                            signal_reason=f"crossover at index {sig['index']}",
                        )
            except Exception:
                logger.exception("Signal scan failed for %s", stock_code)


# ── Stock pool helpers ───────────────────────────────────────────────────────

def _get_stock_pool(scope: str, industry: str = None) -> list[str]:
    """Return list of stock codes for the given scope."""
    from backend.src.db.sqlite import get_db
    from backend.src.db.duckdb import db

    if scope == "watchlist":
        with get_db() as conn:
            rows = conn.execute("SELECT stock_code FROM watchlist ORDER BY stock_code").fetchall()
        return [r["stock_code"] for r in rows]

    if scope == "industry" and industry:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT stock_code FROM stocks WHERE industry = ? AND is_active = 1",
                (industry,)
            ).fetchall()
        return [r["stock_code"] for r in rows]

    rows = db.query(
        "SELECT DISTINCT stock_code FROM daily_kline "
        "WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'"
    ).fetchall()
    codes = [r[0] for r in rows]
    if codes:
        return codes
    with get_db() as conn:
        rows = conn.execute("SELECT stock_code FROM stocks WHERE is_active = 1").fetchall()
    return [r["stock_code"] for r in rows]


# ── Signal Scanning (US2) ────────────────────────────────────────────────────

def scan_signals(model_name: str, signal_type: str,
                 scope: str = "watchlist", industry: str = None,
                 exclude_st: bool = False, exclude_loss: bool = False) -> list[dict]:
    """Scan stocks for BUY or SELL signals using the given model."""
    from backend.src.services.model_service import MaCrossModel
    from backend.src.models.strategy_config import StrategyConfig
    from backend.src.models.position import Position
    from backend.src.models.trade_signal import TradeSignal
    from backend.src.db.sqlite import get_db

    config = StrategyConfig.get(model_name)
    if not config:
        return []

    params = config.get("params", {})
    if isinstance(params, str):
        import json as _json
        params = _json.loads(params)

    model = MaCrossModel(
        short=params.get("short", 5),
        long=params.get("long", 20),
    )

    stock_pool = _get_stock_pool(scope, industry)
    if not stock_pool:
        return []

    # Apply filters
    if exclude_st or exclude_loss:
        with get_db() as conn:
            stock_pool = _apply_stock_filters(conn, stock_pool, exclude_st, exclude_loss)
            if not stock_pool:
                return []

    positions = Position.all(model_name)
    held_codes = {p["stock_code"] for p in positions if p["quantity"] > 0}

    TradeSignal.create_table()
    results = []

    for code in stock_pool:
        is_held = code in held_codes
        if signal_type == "BUY" and is_held:
            continue
        if signal_type == "SELL" and not is_held:
            continue

        try:
            sigs = model.scan_stock(code)
            if not sigs:
                continue
            for s in sigs:
                if s["signal_type"] != signal_type:
                    continue
                with get_db() as conn:
                    r = conn.execute(
                        "SELECT stock_name FROM stocks WHERE stock_code = ?", (code,)
                    ).fetchone()
                    fr = conn.execute(
                        "SELECT pe_ratio FROM stock_fundamentals WHERE stock_code = ? ORDER BY snap_date DESC LIMIT 1",
                        (code,)
                    ).fetchone()
                stock_name = r["stock_name"] if r else code
                pe_ratio = round(fr["pe_ratio"], 1) if fr and fr["pe_ratio"] else None

                signal_id = TradeSignal.create(
                    stock_code=code,
                    model_name=model_name,
                    signal_type=s["signal_type"],
                    signal_price=s["price"],
                    signal_reason=f"MA{params.get('short',5)} {'上穿' if s['signal_type'] == 'BUY' else '下穿'}MA{params.get('long',20)}",
                    trade_date=str(s.get("trade_date", "")),
                    config_id=config["id"],
                )
                with get_db() as conn:
                    conn.execute(
                        "UPDATE trade_signals SET stock_name = ? WHERE id = ?",
                        (stock_name, signal_id)
                    )
                results.append({
                    "id": signal_id,
                    "stock_code": code,
                    "stock_name": stock_name,
                    "signal_type": s["signal_type"],
                    "signal_price": s["price"],
                    "signal_reason": f"MA{params.get('short',5)} {'上穿' if s['signal_type'] == 'BUY' else '下穿'}MA{params.get('long',20)}",
                    "trade_date": str(s.get("trade_date", "")),
                    "pe_ratio": pe_ratio,
                })
        except Exception:
            logger.exception("Scan failed for %s", code)

    return results


def _apply_stock_filters(conn, codes: list, exclude_st: bool, exclude_loss: bool) -> list:
    """Filter stock list by ST name and/or negative EPS."""
    placeholders = ",".join("?" for _ in codes)
    if not placeholders:
        return []

    if exclude_st and exclude_loss:
        rows = conn.execute(f"""
            SELECT s.stock_code FROM stocks s
            LEFT JOIN stock_fundamentals f ON f.stock_code = s.stock_code
                AND f.snap_date = (SELECT MAX(snap_date) FROM stock_fundamentals WHERE stock_code = s.stock_code)
            WHERE s.stock_code IN ({placeholders})
              AND s.stock_name NOT LIKE '%ST%'
              AND (f.eps IS NULL OR f.eps > 0)
        """, codes).fetchall()
    elif exclude_st:
        rows = conn.execute(f"""
            SELECT stock_code FROM stocks
            WHERE stock_code IN ({placeholders})
              AND stock_name NOT LIKE '%ST%'
        """, codes).fetchall()
    elif exclude_loss:
        rows = conn.execute(f"""
            SELECT s.stock_code FROM stocks s
            LEFT JOIN stock_fundamentals f ON f.stock_code = s.stock_code
                AND f.snap_date = (SELECT MAX(snap_date) FROM stock_fundamentals WHERE stock_code = s.stock_code)
            WHERE s.stock_code IN ({placeholders})
              AND (f.eps IS NULL OR f.eps > 0)
        """, codes).fetchall()
    else:
        return codes

    return [r["stock_code"] for r in rows]


# ── Signal Confirmation & Order Creation (US3) ──────────────────────────────

def confirm_signal(signal_id: int, quantity_override: int = None,
                   price_override: float = None) -> dict:
    """Confirm a signal and create an order with auto-filled price/quantity."""
    from backend.src.models.trade_signal import TradeSignal
    from backend.src.models.order import Order
    from backend.src.models.strategy_config import StrategyConfig
    from backend.src.models.position import Position
    from backend.src.db.duckdb import db

    sig = TradeSignal.get(signal_id)
    if not sig:
        return {"error": "Signal not found"}

    model_name = sig["model_name"]
    stock_code = sig["stock_code"]
    price = float(price_override) if price_override else float(sig["signal_price"])
    signal_type = sig["signal_type"]

    config = StrategyConfig.get(model_name)
    capital = config["capital"] if config else 100000
    position_pct = config.get("position_pct", 100) if config else 100

    if signal_type == "BUY":
        if quantity_override:
            quantity = int(quantity_override)
        else:
            available = capital * position_pct / 100
            raw_qty = int(available / price / 100) * 100
            quantity = max(raw_qty, 100)
    else:
        pos = Position.get(stock_code, model_name)
        quantity = int(quantity_override) if quantity_override else (pos["quantity"] if pos else 0)

    if quantity <= 0:
        return {"error": "计算出的数量无效"}

    # Require QMT connection — no local-only fallback
    connector = get_connector()
    if not connector.is_connected():
        return {"error": "QMT 未连接，无法下单。请确保 MiniQMT 已登录。"}

    try:
        qmt_order_id = connector.submit_order(stock_code, signal_type, price, quantity)
    except RuntimeError as e:
        logger.error("QMT order rejected: %s", e)
        return {"error": f"QMT 下单失败: {e}"}

    # Create local order record for UI tracking
    Order.create_table()
    order_id = Order.create(
        stock_code=stock_code,
        order_type=signal_type,
        price=price,
        quantity=quantity,
        signal_id=signal_id,
        model_name=model_name,
        original_price=price,
    )

    # Update position
    Position.create_table()
    pos = Position.get(stock_code, model_name)
    if signal_type == "BUY":
        new_qty = (pos["quantity"] if pos else 0) + quantity
        new_cost = ((pos["avg_cost"] if pos else 0) * (pos["quantity"] if pos else 0) + price * quantity) / new_qty if new_qty > 0 else price
        Position.upsert(
            stock_code=stock_code,
            stock_name=sig.get("stock_name", ""),
            quantity=new_qty,
            avg_cost=new_cost,
            current_price=price,
            model_name=model_name,
        )
    else:
        remaining = (pos["quantity"] if pos else 0) - quantity
        if remaining <= 0:
            Position.upsert(stock_code=stock_code, stock_name=sig.get("stock_name", ""),
                          quantity=0, avg_cost=0, current_price=price, model_name=model_name)
        else:
            Position.upsert(
                stock_code=stock_code,
                stock_name=sig.get("stock_name", ""),
                quantity=remaining,
                avg_cost=pos["avg_cost"],
                current_price=price,
                model_name=model_name,
            )

    TradeSignal.confirm(signal_id)

    return {
        "signal_id": signal_id,
        "order_id": order_id,
        "qmt_order_id": qmt_order_id,
        "qmt_status": "submitted",
        "status": "submitted",
        "stock_code": stock_code,
        "order_type": signal_type,
        "price": price,
        "quantity": quantity,
    }


# ── Order Monitoring (US4) ───────────────────────────────────────────────────

def monitor_orders() -> list[dict]:
    """Check submitted orders and auto-retry stale ones. Returns all orders."""
    from backend.src.models.order import Order
    from backend.src.models.strategy_config import StrategyConfig

    submitted = Order.all_submitted()
    for order in submitted:
        # For simulated trading, auto-fill after 5 seconds
        try:
            from datetime import timedelta
            elapsed = (datetime.now() - datetime.fromisoformat(order["created_at"])).total_seconds()
        except Exception:
            elapsed = 0

        if elapsed > 60:
            # Attempt retry
            if order["retry_count"] >= 3:
                Order.mark_failed(order["order_id"])
                logger.warning("Order %d exceeded max retries", order["order_id"])
                continue

            # Check price deviation
            from backend.src.db.duckdb import db
            row = db.query(
                "SELECT close FROM daily_kline WHERE stock_code = ? ORDER BY trade_date DESC LIMIT 1",
                (order["stock_code"],)
            ).fetchone()
            if row:
                latest_price = row[0]
                orig_price = order["original_price"] or order["price"]
                deviation = abs(latest_price - orig_price) / orig_price if orig_price else 0
                if deviation > 0.03:
                    logger.info("Order %d price deviation %.2f%% too large, pausing",
                                order["order_id"], deviation * 100)
                    continue

                retry_order(order["order_id"])
    return Order.all()


def retry_order(order_id: int) -> dict:
    """Cancel order and create new one with latest price."""
    from backend.src.models.order import Order
    from backend.src.db.duckdb import db

    old = Order.get(order_id)
    if not old:
        return {"error": "Order not found"}
    if old["status"] not in ("submitted", "cancelled"):
        return {"error": "只能重试已提交或已撤单的订单"}

    row = db.query(
        "SELECT close FROM daily_kline WHERE stock_code = ? ORDER BY trade_date DESC LIMIT 1",
        (old["stock_code"],)
    ).fetchone()
    latest_price = row[0] if row else old["price"]

    orig_price = old["original_price"] or old["price"]
    deviation = abs(latest_price - orig_price) / orig_price if orig_price else 0
    if deviation > 0.03:
        return {"error": f"价格偏差 {deviation*100:.1f}% 超过3%，请手动确认"}

    retry_count = (old["retry_count"] or 0) + 1
    if retry_count > 3:
        Order.mark_failed(order_id)
        return {"error": "超过最大重试次数"}

    # Cancel old order in QMT
    connector = get_connector()
    if connector.is_connected():
        try:
            connector.cancel_order(order_id)
        except Exception:
            logger.warning("Failed to cancel QMT order %d", order_id)
    Order.cancel(order_id)

    # Submit new order to QMT
    if not connector.is_connected():
        return {"error": "QMT 未连接，无法重试下单"}
    try:
        connector.submit_order(old["stock_code"], old["order_type"], latest_price, old["quantity"])
    except RuntimeError as e:
        return {"error": f"QMT 重试下单失败: {e}"}

    # Create new local order record
    Order.create_table()
    new_id = Order.create(
        stock_code=old["stock_code"],
        order_type=old["order_type"],
        price=latest_price,
        quantity=old["quantity"],
        signal_id=old["signal_id"],
        model_name=old.get("model_name", ""),
        retry_count=retry_count,
        original_price=orig_price,
    )
    return {
        "order_id": order_id,
        "new_order_id": new_id,
        "status": "submitted",
        "retry_count": retry_count,
    }


# ── Model Performance (US5) ──────────────────────────────────────────────────

def get_model_performance(model_name: str) -> dict:
    """Calculate per-model performance metrics."""
    from backend.src.models.strategy_config import StrategyConfig
    from backend.src.models.position import Position

    config = StrategyConfig.get(model_name)
    initial_capital = config["capital"] if config else 100000

    positions = Position.all(model_name)
    total_market_value = sum(p.get("market_value", 0) for p in positions)
    total_pnl = sum(p.get("profit_loss", 0) for p in positions)
    available_cash = initial_capital
    total_asset = available_cash + total_market_value
    total_return = (total_asset - 100000) / 100000 if total_asset else 0

    return {
        "model_name": model_name,
        "initial_capital": 100000,
        "available_cash": available_cash,
        "market_value": total_market_value,
        "total_asset": total_asset,
        "total_return": total_return,
        "total_return_pct": total_return * 100,
        "total_pnl": total_pnl,
        "positions": positions,
    }
