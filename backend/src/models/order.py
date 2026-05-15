from backend.src.db.sqlite import get_db


class Order:
    @staticmethod
    def create_table():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(10) NOT NULL,
                    order_type VARCHAR(10) NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    signal_id INTEGER,
                    model_name VARCHAR(50) DEFAULT '',
                    retry_count INTEGER DEFAULT 0,
                    original_price REAL,
                    status VARCHAR(20) DEFAULT 'submitted',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for col, col_type in [("model_name", "VARCHAR(50) DEFAULT ''"),
                                   ("retry_count", "INTEGER DEFAULT 0"),
                                   ("original_price", "REAL")]:
                try:
                    conn.execute(f"ALTER TABLE orders ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

    @staticmethod
    def create(stock_code: str, order_type: str, price: float,
               quantity: int, signal_id: int = None,
               model_name: str = "", retry_count: int = 0,
               original_price: float = None) -> int:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO orders (stock_code, order_type, price, quantity, signal_id, "
                "model_name, retry_count, original_price) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (stock_code, order_type, price, quantity, signal_id,
                 model_name, retry_count, original_price)
            )
            return cur.lastrowid

    @staticmethod
    def get(order_id: int) -> dict | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def cancel(order_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = ?",
                (order_id,)
            )

    @staticmethod
    def fill(order_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE orders SET status = 'filled' WHERE id = ?",
                (order_id,)
            )

    @staticmethod
    def mark_failed(order_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE orders SET status = 'failed' WHERE id = ?",
                (order_id,)
            )

    @staticmethod
    def update_retry(order_id: int, new_order_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE orders SET retry_count = retry_count + 1 WHERE id = ?",
                (order_id,)
            )

    @staticmethod
    def all(model_name: str = None) -> list:
        with get_db() as conn:
            if model_name:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE model_name = ? ORDER BY created_at DESC",
                    (model_name,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def all_submitted() -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE status = 'submitted' ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]
