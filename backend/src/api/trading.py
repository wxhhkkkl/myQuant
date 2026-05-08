import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from backend.src.templates import templates
from backend.src.models.trade_signal import TradeSignal
from backend.src.models.order import Order

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """Trading page: signals list + order form + order status."""
    return templates.TemplateResponse(request, "pages/trading.html", {})


@router.get("/api/signals", response_class=HTMLResponse)
async def list_signals(request: Request):
    """Return signals list as HTML component."""
    signals = TradeSignal.all()
    return templates.TemplateResponse(request, "components/signals.html", {
        "signals": signals,
    })


@router.post("/api/signals/{signal_id}/confirm")
async def confirm_signal(signal_id: int):
    sig = TradeSignal.get(signal_id)
    if sig is None:
        return JSONResponse({"error": "Signal not found"}, status_code=404)
    TradeSignal.confirm(signal_id)
    return {"status": "confirmed", "signal_id": signal_id}


@router.post("/api/signals/{signal_id}/dismiss")
async def dismiss_signal(signal_id: int):
    sig = TradeSignal.get(signal_id)
    if sig is None:
        return JSONResponse({"error": "Signal not found"}, status_code=404)
    TradeSignal.dismiss(signal_id)
    return {"status": "dismissed", "signal_id": signal_id}


@router.get("/api/orders", response_class=HTMLResponse)
async def list_orders(request: Request):
    """Return orders list as HTML component."""
    orders = Order.all()
    return templates.TemplateResponse(request, "components/orders.html", {
        "orders": orders,
    })


@router.post("/api/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=422)

    stock_code = data.get("stock_code")
    order_type = data.get("order_type")
    price = data.get("price")
    quantity = data.get("quantity")
    signal_id = data.get("signal_id")

    if not all([stock_code, order_type, price, quantity]):
        return JSONResponse({"error": "stock_code, order_type, price, quantity required"}, status_code=422)

    try:
        order_id = Order.create(
            stock_code=stock_code,
            order_type=order_type,
            price=float(price),
            quantity=int(quantity),
            signal_id=signal_id,
        )
    except Exception:
        return JSONResponse({"error": "Failed to create order"}, status_code=422)

    return {"id": order_id, "status": "submitted"}


@router.delete("/api/orders/{order_id}")
async def cancel_order(order_id: int):
    order = Order.get(order_id)
    if order is None:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    Order.cancel(order_id)
    return {"status": "cancelled", "order_id": order_id}
