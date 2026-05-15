from backend.src.db.sqlite import get_db


class Position:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL,
                    stock_name VARCHAR(50),
                    model_name VARCHAR(50) NOT NULL DEFAULT 'default',
                    quantity INTEGER NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    current_price REAL NOT NULL DEFAULT 0,
                    market_value REAL NOT NULL DEFAULT 0,
                    profit_loss REAL NOT NULL DEFAULT 0,
                    profit_loss_pct REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, model_name)
                )
            """)
            # Add model_name column if upgrading from older schema
            try:
                conn.execute("ALTER TABLE positions ADD COLUMN model_name VARCHAR(50) DEFAULT 'default'")
            except Exception:
                pass

    @staticmethod
    def upsert(stock_code: str, stock_name: str = None, quantity: int = 0,
               avg_cost: float = 0.0, current_price: float = 0.0,
               model_name: str = "default"):
        market_value = quantity * current_price
        profit_loss = quantity * (current_price - avg_cost) if avg_cost else 0.0
        profit_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0.0
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM positions WHERE stock_code = ? AND model_name = ?",
                (stock_code, model_name)
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE positions SET
                        stock_name = ?, quantity = ?, avg_cost = ?,
                        current_price = ?, market_value = ?, profit_loss = ?,
                        profit_loss_pct = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE stock_code = ? AND model_name = ?
                """, (stock_name, quantity, avg_cost, current_price, market_value,
                      profit_loss, profit_loss_pct, stock_code, model_name))
            else:
                conn.execute("""
                    INSERT INTO positions (stock_code, stock_name, model_name, quantity, avg_cost,
                        current_price, market_value, profit_loss, profit_loss_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (stock_code, stock_name, model_name, quantity, avg_cost, current_price,
                      market_value, profit_loss, profit_loss_pct))

    @staticmethod
    def all(model_name: str = None) -> list:
        with get_db() as conn:
            if model_name:
                rows = conn.execute(
                    "SELECT * FROM positions WHERE model_name = ? ORDER BY market_value DESC",
                    (model_name,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM positions ORDER BY market_value DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get(stock_code: str, model_name: str = "default") -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE stock_code = ? AND model_name = ?",
                (stock_code, model_name)
            ).fetchone()
        return dict(row) if row else None
