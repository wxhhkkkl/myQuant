from backend.src.db.sqlite import get_db


class Position:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL UNIQUE,
                    stock_name VARCHAR(50),
                    quantity INTEGER NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    current_price REAL NOT NULL DEFAULT 0,
                    market_value REAL NOT NULL DEFAULT 0,
                    profit_loss REAL NOT NULL DEFAULT 0,
                    profit_loss_pct REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def upsert(stock_code: str, stock_name: str = None, quantity: int = 0,
               avg_cost: float = 0.0, current_price: float = 0.0):
        market_value = quantity * current_price
        profit_loss = quantity * (current_price - avg_cost) if avg_cost else 0.0
        profit_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        with get_db() as conn:
            conn.execute("""
                INSERT INTO positions (stock_code, stock_name, quantity, avg_cost,
                    current_price, market_value, profit_loss, profit_loss_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code) DO UPDATE SET
                    stock_name = excluded.stock_name,
                    quantity = excluded.quantity,
                    avg_cost = excluded.avg_cost,
                    current_price = excluded.current_price,
                    market_value = excluded.market_value,
                    profit_loss = excluded.profit_loss,
                    profit_loss_pct = excluded.profit_loss_pct,
                    updated_at = CURRENT_TIMESTAMP
            """, (stock_code, stock_name, quantity, avg_cost, current_price,
                  market_value, profit_loss, profit_loss_pct))

    @staticmethod
    def all() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM positions ORDER BY market_value DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(stock_code: str) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE stock_code = ?", (stock_code,)
            ).fetchone()
        return dict(row) if row else None
