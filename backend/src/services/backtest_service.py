"""
Backtest engine: daily iteration with buy/sell state machine.
"""
import logging
import uuid
from datetime import datetime

from backend.src.db.duckdb import db
from backend.src.services.model_service import MaCrossModel

logger = logging.getLogger(__name__)


def run_backtest(stock_code: str, kline: list, signals: list,
                 initial_capital: float = 100000) -> dict:
    """
    Run backtest simulation.

    Args:
        stock_code: Stock code being tested.
        kline: List of daily K-line dicts with trade_date, close, open, high, low.
        signals: List of signal dicts with trade_date, signal_type (BUY/SELL), price.
        initial_capital: Starting capital.

    Returns:
        Dict with: total_return, annual_return, max_drawdown, sharpe_ratio,
                   trade_count, win_rate, trades, initial_capital, final_capital.
    """
    # Build date → close price map
    price_map = {r["trade_date"]: r["close"] for r in kline}
    dates = sorted(price_map.keys())

    # Build signal map by date
    signal_map = {}
    for s in signals:
        signal_map[s.get("trade_date", "")] = s["signal_type"]

    cash = initial_capital
    position = 0  # shares held
    trades = []
    equity_curve = [initial_capital]

    for date in dates:
        price = price_map[date]
        sig = signal_map.get(date)

        if sig == "BUY" and cash > 0:
            # Buy with all available cash
            quantity = int(cash / price)
            if quantity > 0:
                cost = quantity * price
                cash -= cost
                position = quantity
                trades.append({
                    "trade_date": date, "trade_type": "BUY",
                    "price": price, "quantity": quantity,
                    "profit": None,
                })

        elif sig == "SELL" and position > 0:
            # Sell all held shares
            revenue = position * price
            buy_trade = next(
                (t for t in reversed(trades) if t["trade_type"] == "BUY" and t.get("profit") is None),
                None
            )
            profit = revenue - (buy_trade["price"] * position) if buy_trade else 0
            if buy_trade:
                buy_trade["profit"] = profit

            cash += revenue
            position = 0
            trades.append({
                "trade_date": date, "trade_type": "SELL",
                "price": price, "quantity": position if position else trades[-1]["quantity"] if trades else 0,
                "profit": profit,
            })

        # Track daily equity
        equity = cash + position * price
        equity_curve.append(equity)

    # Calculate metrics
    final_capital = equity_curve[-1]
    total_return = (final_capital - initial_capital) / initial_capital if initial_capital > 0 else 0

    # Annual return (approximate)
    n_days = len(dates) if dates else 1
    annual_return = ((1 + total_return) ** (365 / n_days) - 1) if total_return > -1 and n_days > 0 else 0

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd

    # Win rate
    completed = [t for t in trades if t.get("profit") is not None]
    wins = [t for t in completed if t["profit"] > 0]
    win_rate = len(wins) / len(completed) if completed else 0

    # Sharpe ratio (simplified: using daily returns)
    if len(equity_curve) > 1:
        daily_returns = [
            (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve)) if equity_curve[i - 1] > 0
        ]
        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            var_ret = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
            sharpe = (mean_ret / (var_ret ** 0.5)) * (252 ** 0.5) if var_ret > 0 else 0
        else:
            sharpe = 0
    else:
        sharpe = 0

    # Store in DuckDB
    run_id = str(uuid.uuid4())
    db.execute("""
        INSERT INTO backtest_results
            (run_id, model_name, model_params, stock_code, start_date, end_date,
             initial_capital, final_capital, total_return, annual_return,
             max_drawdown, sharpe_ratio, trade_count, win_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, "ma_cross", "{}", stock_code,
          dates[0] if dates else "", dates[-1] if dates else "",
          initial_capital, final_capital, total_return, annual_return,
          max_dd, sharpe, len(trades), win_rate))

    # Get the current max id for manual increment
    max_id_row = db.query("SELECT COALESCE(MAX(id), 0) FROM backtest_trades").fetchone()
    next_id = (max_id_row[0] if max_id_row else 0) + 1

    for t in trades:
        db.execute("""
            INSERT INTO backtest_trades (id, run_id, trade_date, trade_type, price, quantity, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (next_id, run_id, t["trade_date"], t["trade_type"], t["price"], t["quantity"],
              t.get("profit")))
        next_id += 1

    return {
        "run_id": run_id,
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "total_return": round(total_return, 6),
        "annual_return": round(annual_return, 6),
        "max_drawdown": round(max_dd, 6),
        "sharpe_ratio": round(sharpe, 4),
        "trade_count": len(trades),
        "win_rate": round(win_rate, 4),
        "trades": trades,
    }
